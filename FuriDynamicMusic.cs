// Furi Dynamic Music Mod
// Copyright (c) 2026 LeonKraim
// Licensed under the "Furi Dynamic Music Mod License".
// See the file "LICENSE.md" for the full license text.

using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
using BepInEx;
using BepInEx.Configuration;
using HarmonyLib;
using UnityEngine;

namespace FuriDynamicMusic
{
    [BepInPlugin(PluginGuid, PluginName, PluginVersion)]
    public sealed class DynamicMusicPlugin : BaseUnityPlugin
    {
        public const string PluginGuid = "io.github.furi-modding.dynamicmusic";
        public const string PluginName = "Furi Native Music Pack";
        public const string PluginVersion = "4.1.2";

        internal static DynamicMusicPlugin Instance;
        internal new static BepInEx.Logging.ManualLogSource Logger;

        private ConfigEntry<string> activePack;

        private MusicPack pack;
        private WavePlayer player;
        private float musicVolume = 100f;
        private bool bindingsReady;
        private float bindNextTickAt;
        private int bindState;

        private static MethodInfo getIdFromStringMethod;
        private static MethodInfo executeActionOnEventMethod;

        private void Awake()
        {
            Instance = this;
            Logger = base.Logger;

            activePack = Config.Bind("General", "Active pack", "",
                "Folder name below plugins/FuriDynamicMusic/packs. Leave blank to disable.");

            string pluginRoot = Path.GetDirectoryName(Info.Location);
            if (string.IsNullOrEmpty(pluginRoot)) pluginRoot = Path.GetFullPath(".");

            if (string.IsNullOrWhiteSpace(activePack.Value))
            {
                Logger.LogWarning("No active pack configured; plugin is idle.");
                return;
            }

            string packsDir = Path.Combine(pluginRoot, "packs");
            string manifestPath = ResolvePack(packsDir, activePack.Value.Trim());
            if (manifestPath == null)
            {
                Logger.LogWarning("No usable pack found in " + packsDir + " for active pack '" + activePack.Value + "'.");
                return;
            }

            string packRoot = Path.GetDirectoryName(manifestPath);

            try
            {
                string json = File.ReadAllText(manifestPath);
                pack = MusicPack.Parse(json, packRoot);
                Logger.LogInfo("Loaded pack '" + pack.Name + "' with " + pack.Cues.Count + " cues and " + pack.Bindings.Count + " bindings.");
            }
            catch (Exception e)
            {
                Logger.LogError("Failed to parse manifest: " + e.Message);
                return;
            }

            player = new WavePlayer();
            bindState = 1;

            try
            {
                var harmony = new Harmony(PluginGuid);
                PatchSoundManager(harmony);
                Logger.LogInfo("Harmony patches applied.");
            }
            catch (Exception e)
            {
                Logger.LogError("Harmony patching failed: " + e.ToString());
            }
        }

        // Find the manifest of the configured pack. The configured name does not have to
        // match the folder name exactly: case is ignored, a folder that contains the
        // configured name (or is contained in it) is accepted, and if only one pack
        // folder exists it is used as a last resort.
        private string ResolvePack(string packsDir, string wanted)
        {
            string exact = Path.Combine(packsDir, wanted, "manifest.json");
            if (File.Exists(exact))
                return exact;

            string wantedLower = wanted.ToLowerInvariant();
            string containsMatch = null;
            try
            {
                foreach (string dir in Directory.GetDirectories(packsDir))
                {
                    string name = Path.GetFileName(dir);
                    string lower = name.ToLowerInvariant();
                    if (lower == wantedLower)
                        return Path.Combine(dir, "manifest.json");
                    if (containsMatch == null && (lower.Contains(wantedLower) || wantedLower.Contains(lower)))
                        containsMatch = Path.Combine(dir, "manifest.json");
                }
                if (containsMatch != null && File.Exists(containsMatch))
                {
                    Logger.LogInfo("Active pack '" + wanted + "' not found by exact name; using '" + Path.GetFileName(Path.GetDirectoryName(containsMatch)) + "'.");
                    return containsMatch;
                }
                string[] dirs = Directory.GetDirectories(packsDir);
                if (dirs.Length == 1)
                {
                    string only = Path.Combine(dirs[0], "manifest.json");
                    if (File.Exists(only))
                    {
                        Logger.LogInfo("Active pack '" + wanted + "' not found; using the only available pack '" + Path.GetFileName(dirs[0]) + "'.");
                        return only;
                    }
                }
            }
            catch (Exception e)
            {
                Logger.LogWarning("Could not search packs folder: " + e.Message);
            }
            return null;
        }

        private void PatchSoundManager(Harmony harmony)
        {
            Type smType = ResolveType("Assembly-CSharp", "SoundManager");
            if (smType == null)
            {
                Logger.LogError("Cannot resolve SoundManager type.");
                return;
            }

            const BindingFlags NF = BindingFlags.Static | BindingFlags.NonPublic;
            const BindingFlags IF = BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic;

            MethodInfo postMusicEvent = smType.GetMethod("PostMusicEvent", IF, null,
                new Type[] { typeof(uint), typeof(GameObject) }, null);
            if (postMusicEvent != null)
            {
                harmony.Patch(postMusicEvent,
                    postfix: new HarmonyMethod(typeof(Patches).GetMethod("PostMusicEventPostfix", NF)));
                Logger.LogInfo("Patched SoundManager.PostMusicEvent");
            }

            MethodInfo postEvent = smType.GetMethod("PostEvent", IF, null,
                new Type[] { typeof(uint), typeof(GameObject) }, null);
            if (postEvent != null)
            {
                harmony.Patch(postEvent,
                    postfix: new HarmonyMethod(typeof(Patches).GetMethod("PostEventPostfix", NF)));
                Logger.LogInfo("Patched SoundManager.PostEvent");
            }

            MethodInfo setState = smType.GetMethod("SetState", IF, null,
                new Type[] { typeof(uint), typeof(uint) }, null);
            if (setState != null)
            {
                harmony.Patch(setState,
                    postfix: new HarmonyMethod(typeof(Patches).GetMethod("SetStatePostfix", NF)));
                Logger.LogInfo("Patched SoundManager.SetState");
            }
        }

        private void Update()
        {
            if (bindState > 0 && bindState < 4) TickBind();
            if (player == null || !player.IsOpen) return;

            float ts = Time.timeScale;
            if (ts <= 0.0001f && !player.IsPausedByGame)
            {
                player.IsPausedByGame = true;
                player.Pause();
            }
            else if (ts > 0.0001f && player.IsPausedByGame)
            {
                player.IsPausedByGame = false;
                if (!player.IsPausedByFocus) player.Resume();
            }
        }

        private void OnApplicationFocus(bool hasFocus)
        {
            if (player == null || !player.IsOpen) return;
            if (!hasFocus)
            {
                player.IsPausedByFocus = true;
                player.Pause();
            }
            else
            {
                player.IsPausedByFocus = false;
                if (!player.IsPausedByGame) player.Resume();
            }
        }

        private void OnApplicationPause(bool paused)
        {
            if (player == null || !player.IsOpen) return;
            if (paused)
            {
                player.IsPausedByFocus = true;
                player.Pause();
            }
            else
            {
                player.IsPausedByFocus = false;
                if (!player.IsPausedByGame) player.Resume();
            }
        }

        private void OnDestroy()
        {
            if (player != null) player.Dispose();
        }

        private void OnApplicationQuit()
        {
            if (player != null) player.Dispose();
        }

        private void TickBind()
        {
            float now = Time.realtimeSinceStartup;
            if (now < bindNextTickAt) return;
            bindNextTickAt = now + 0.25f;
            const BindingFlags F = BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.FlattenHierarchy;

            if (bindState == 1)
            {
                Type smT = ResolveType("Assembly-CSharp", "SoundManager");
                if (smT == null) return;
                try
                {
                    PropertyInfo p = smT.GetProperty("IsReady", F);
                    object r = p != null ? p.GetValue(null, null) : null;
                    if (r is bool && (bool)r) { Logger.LogInfo("SoundManager ready."); bindState = 2; return; }
                }
                catch { }
                return;
            }
            if (bindState == 2)
            {
                Type st = ResolveType("Assembly-CSharp", "SettingsManager");
                try
                {
                    if (st != null)
                    {
                        PropertyInfo ip = st.GetProperty("Instance", F);
                        object s = ip != null ? ip.GetValue(null, null) : null;
                        if (s != null)
                        {
                            PropertyInfo dp = st.GetProperty("Data");
                            object data = dp != null ? dp.GetValue(s, null) : null;
                            if (data != null)
                            {
                                FieldInfo af = data.GetType().GetField("_audioSettings",
                                    BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic);
                                object audio = af != null ? af.GetValue(data) : null;
                                if (audio != null)
                                {
                                    try
                                    {
                                        EventInfo evt = audio.GetType().GetEvent("BusVolumeChanged");
                                        if (evt != null)
                                            evt.AddEventHandler(audio, new Action<uint, float>(OnVolumeChanged));
                                        MethodInfo m = audio.GetType().GetMethod("GetBusVolume", new Type[] { typeof(uint) });
                                        if (m != null)
                                        {
                                            object v = m.Invoke(audio, new object[] { 1006694123u });
                                            if (v is float) musicVolume = (float)v;
                                        }
                                    }
                                    catch { }
                                    bindState = 3;
                                    return;
                                }
                            }
                        }
                    }
                }
                catch { }
                return;
            }
            if (bindState == 3)
            {
                ResolveBindings();
                bindingsReady = true;
                bindState = 4;
                Logger.LogInfo("Bindings resolved. Mod is active.");
            }
        }

        private void ResolveBindings()
        {
            CacheWwiseMethods();
            foreach (Binding b in pack.Bindings)
            {
                if (b.TriggerType == TriggerType.EventId)
                {
                    b.ResolvedEventId = b.EventIdValue;
                }
                else if (b.TriggerType == TriggerType.Event)
                {
                    b.ResolvedEventId = WwiseGetIdFromString(b.EventName);
                }
                else if (b.TriggerType == TriggerType.State)
                {
                    b.ResolvedStateGroup = WwiseGetIdFromString(b.StateGroup);
                    b.ResolvedStateId = WwiseGetIdFromString(b.StateName);
                }
                Logger.LogInfo("Binding: " + b.TriggerRaw + " -> " + (b.Action == "stop" ? "(stop)" : b.CueId));
            }
        }

        private void CacheWwiseMethods()
        {
            Type akType = ResolveType("AK.Wwise.Unity.API", "AkSoundEngine");
            if (akType == null)
            {
                Logger.LogError("Cannot resolve AkSoundEngine for ID resolution.");
                return;
            }
            getIdFromStringMethod = akType.GetMethod("GetIDFromString",
                BindingFlags.Static | BindingFlags.Public, null, new Type[] { typeof(string) }, null);

            executeActionOnEventMethod = akType.GetMethod("ExecuteActionOnEvent",
                BindingFlags.Static | BindingFlags.Public, null,
                new Type[] { typeof(uint), typeof(int), typeof(ulong), typeof(int), typeof(int) }, null);
            if (executeActionOnEventMethod == null)
            {
                MethodInfo[] methods = akType.GetMethods(BindingFlags.Static | BindingFlags.Public);
                for (int i = 0; i < methods.Length; i++)
                {
                    if (methods[i].Name == "ExecuteActionOnEvent")
                    {
                        ParameterInfo[] ps = methods[i].GetParameters();
                        if (ps.Length == 5 && ps[0].ParameterType == typeof(uint) && ps[2].ParameterType == typeof(ulong))
                        {
                            executeActionOnEventMethod = methods[i];
                            break;
                        }
                    }
                }
            }
        }

        private uint WwiseGetIdFromString(string name)
        {
            if (getIdFromStringMethod == null) return 0;
            try
            {
                object result = getIdFromStringMethod.Invoke(null, new object[] { name });
                if (result is uint) return (uint)result;
            }
            catch { }
            return 0;
        }

        private void OnVolumeChanged(uint rtpc, float v)
        {
            if (rtpc != 1006694123u) return;
            musicVolume = v;
            if (player != null) player.SetVolume(v / 100f);
        }

        internal void OnEventPosted(uint eventId, GameObject go)
        {
            if (!bindingsReady || pack == null) return;

            for (int i = 0; i < pack.Bindings.Count; i++)
            {
                Binding b = pack.Bindings[i];
                if (b.ResolvedEventId != eventId) continue;
                if (b.TriggerType == TriggerType.State) continue;

                if (b.Action == "stop")
                {
                    Logger.LogInfo("Stop trigger fired (event " + eventId + ")");
                    StopCustomMusic();
                    return;
                }

                Cue cue = pack.GetCue(b.CueId);
                if (cue == null)
                {
                    Logger.LogWarning("Binding references unknown cue: " + b.CueId);
                    return;
                }

                Logger.LogInfo("Play trigger fired (event " + eventId + ") -> cue '" + cue.Id + "'");
                BlockOriginalMusic(eventId, go);
                PlayCue(cue);
                return;
            }

            if (player != null && player.IsOpen && eventId == 452547817u)
            {
                Logger.LogInfo("STOP_ALL fired; stopping custom track.");
                StopCustomMusic();
            }
        }

        internal void OnStateChanged(uint stateGroup, uint stateId)
        {
            if (!bindingsReady || pack == null) return;

            for (int i = 0; i < pack.Bindings.Count; i++)
            {
                Binding b = pack.Bindings[i];
                if (b.TriggerType != TriggerType.State) continue;
                if (b.ResolvedStateGroup != stateGroup || b.ResolvedStateId != stateId) continue;

                Cue cue = pack.GetCue(b.CueId);
                if (cue == null) return;

                Logger.LogInfo("State trigger fired (" + stateGroup + "." + stateId + ") -> cue '" + cue.Id + "'");
                PlayCue(cue);
                return;
            }
        }

        private void BlockOriginalMusic(uint eventId, GameObject go)
        {
            if (executeActionOnEventMethod == null) return;
            try
            {
                ulong goId = (go != null) ? (ulong)go.GetInstanceID() : 0uL;
                executeActionOnEventMethod.Invoke(null, new object[] { eventId, 0, goId, 0, 4 });
            }
            catch (Exception e)
            {
                Logger.LogWarning("Failed to block original music: " + e.Message);
            }
        }

        private void PlayCue(Cue cue)
        {
            if (player == null) return;
            string path = Path.Combine(pack.PackRoot, cue.File);
            if (!File.Exists(path))
            {
                Logger.LogWarning("Audio file not found: " + path);
                return;
            }
            string introPath = null;
            if (!string.IsNullOrEmpty(cue.IntroFile))
            {
                string introFull = Path.Combine(pack.PackRoot, cue.IntroFile);
                if (File.Exists(introFull)) introPath = introFull;
                else Logger.LogWarning("Intro audio file not found: " + introFull);
            }
            if (introPath != null)
                player.PlayIntroThenLoop(introPath, path, cue.Loop, musicVolume / 100f);
            else
                player.Play(path, cue.Loop, musicVolume / 100f);
        }

        private void StopCustomMusic()
        {
            if (player != null) player.Stop();
        }

        private static Type ResolveType(string asmName, string typeName)
        {
            try
            {
                foreach (Assembly a in AppDomain.CurrentDomain.GetAssemblies())
                {
                    if (a.GetName().Name == asmName)
                    {
                        Type t = a.GetType(typeName);
                        if (t != null) return t;
                    }
                }
            }
            catch { }
            return null;
        }
    }

    internal static class Patches
    {
        internal static void PostMusicEventPostfix(uint eventID, GameObject gameObject)
        {
            if (DynamicMusicPlugin.Instance != null)
                DynamicMusicPlugin.Instance.OnEventPosted(eventID, gameObject);
        }

        internal static void PostEventPostfix(uint eventID, GameObject gameObject)
        {
            if (DynamicMusicPlugin.Instance != null)
                DynamicMusicPlugin.Instance.OnEventPosted(eventID, gameObject);
        }

        internal static void SetStatePostfix(uint in_stateGroup, uint in_state)
        {
            if (DynamicMusicPlugin.Instance != null)
                DynamicMusicPlugin.Instance.OnStateChanged(in_stateGroup, in_state);
        }
    }

    internal enum TriggerType { Event, EventId, State }

    internal sealed class Binding
    {
        public TriggerType TriggerType;
        public string TriggerRaw;
        public string EventName;
        public uint EventIdValue;
        public string StateGroup;
        public string StateName;
        public string CueId;
        public string Action = "play";
        public bool BlockOriginal = true;
        public float FadeSeconds;

        public uint ResolvedEventId;
        public uint ResolvedStateGroup;
        public uint ResolvedStateId;

        public static Binding ParseTrigger(string trigger)
        {
            Binding b = new Binding();
            b.TriggerRaw = trigger;
            if (trigger.StartsWith("eventid:"))
            {
                b.TriggerType = TriggerType.EventId;
                b.EventIdValue = uint.Parse(trigger.Substring(8), CultureInfo.InvariantCulture);
            }
            else if (trigger.StartsWith("event:"))
            {
                b.TriggerType = TriggerType.Event;
                b.EventName = trigger.Substring(6);
            }
            else if (trigger.StartsWith("state:"))
            {
                b.TriggerType = TriggerType.State;
                string rest = trigger.Substring(6);
                int dot = rest.IndexOf('.');
                if (dot > 0)
                {
                    b.StateGroup = rest.Substring(0, dot);
                    b.StateName = rest.Substring(dot + 1);
                }
                else
                {
                    b.StateGroup = rest;
                    b.StateName = "";
                }
            }
            return b;
        }
    }

    internal sealed class Cue
    {
        public string Id;
        public string File;
        public string IntroFile;
        public bool Loop;
        public float StartSeconds;
        public float Bpm = 120f;
        public int BeatsPerBar = 4;
        public float GainDb;
    }

    internal sealed class MusicPack
    {
        public string Name = "";
        public float GainDb;
        public string PackRoot;
        public List<Cue> Cues = new List<Cue>();
        public List<Binding> Bindings = new List<Binding>();

        public Cue GetCue(string id)
        {
            for (int i = 0; i < Cues.Count; i++)
                if (Cues[i].Id == id) return Cues[i];
            return null;
        }

        public static MusicPack Parse(string json, string packRoot)
        {
            object root = MiniJson.Parse(json);
            Dictionary<string, object> obj = root as Dictionary<string, object>;
            if (obj == null) throw new Exception("Manifest root is not an object.");

            MusicPack pack = new MusicPack();
            pack.PackRoot = packRoot;
            if (obj.ContainsKey("name")) pack.Name = obj["name"] as string ?? "";
            if (obj.ContainsKey("gain_db")) pack.GainDb = Convert.ToSingle(obj["gain_db"], CultureInfo.InvariantCulture);

            List<object> cuesList = obj.ContainsKey("cues") ? obj["cues"] as List<object> : null;
            if (cuesList != null)
            {
                foreach (object item in cuesList)
                {
                    Dictionary<string, object> c = item as Dictionary<string, object>;
                    if (c == null) continue;
                    Cue cue = new Cue();
                    cue.Id = GetStr(c, "id", "");
                    cue.File = GetStr(c, "file", "");
                    cue.IntroFile = GetStr(c, "intro_file", "");
                    cue.Loop = GetBool(c, "loop", true);
                    cue.StartSeconds = GetFlt(c, "start_seconds", 0f);
                    cue.Bpm = GetFlt(c, "bpm", 120f);
                    cue.BeatsPerBar = (int)GetFlt(c, "beats_per_bar", 4f);
                    cue.GainDb = GetFlt(c, "gain_db", 0f);
                    pack.Cues.Add(cue);
                }
            }

            List<object> bindingsList = obj.ContainsKey("bindings") ? obj["bindings"] as List<object> : null;
            if (bindingsList != null)
            {
                foreach (object item in bindingsList)
                {
                    Dictionary<string, object> bObj = item as Dictionary<string, object>;
                    if (bObj == null) continue;
                    string trigger = GetStr(bObj, "trigger", "");
                    if (string.IsNullOrEmpty(trigger)) continue;
                    Binding binding = Binding.ParseTrigger(trigger);
                    binding.CueId = GetStr(bObj, "cue", "");
                    binding.Action = GetStr(bObj, "action", "play");
                    binding.BlockOriginal = GetBool(bObj, "block_original", true);
                    binding.FadeSeconds = GetFlt(bObj, "fade_seconds", 0f);
                    pack.Bindings.Add(binding);
                }
            }
            return pack;
        }

        private static string GetStr(Dictionary<string, object> d, string k, string def)
        { object v; return d.TryGetValue(k, out v) && v is string ? (string)v : def; }
        private static bool GetBool(Dictionary<string, object> d, string k, bool def)
        { object v; return d.TryGetValue(k, out v) && v is bool ? (bool)v : def; }
        private static float GetFlt(Dictionary<string, object> d, string k, float def)
        { object v; if (d.TryGetValue(k, out v)) { try { return Convert.ToSingle(v, CultureInfo.InvariantCulture); } catch { } } return def; }
    }

    internal sealed class WavePlayer : IDisposable
    {
        [DllImport("winmm.dll")] private static extern uint waveOutOpen(out IntPtr phwo, uint uDeviceID, ref WAVEFORMATEX pwfx, IntPtr dwCallback, IntPtr dwInstance, uint fdwOpen);
        [DllImport("winmm.dll")] private static extern uint waveOutClose(IntPtr hwo);
        [DllImport("winmm.dll")] private static extern uint waveOutPrepareHeader(IntPtr hwo, IntPtr pwh, uint cbwh);
        [DllImport("winmm.dll")] private static extern uint waveOutUnprepareHeader(IntPtr hwo, IntPtr pwh, uint cbwh);
        [DllImport("winmm.dll")] private static extern uint waveOutWrite(IntPtr hwo, IntPtr pwh, uint cbwh);
        [DllImport("winmm.dll")] private static extern uint waveOutPause(IntPtr hwo);
        [DllImport("winmm.dll")] private static extern uint waveOutRestart(IntPtr hwo);
        [DllImport("winmm.dll")] private static extern uint waveOutReset(IntPtr hwo);

        private const uint WAVE_MAPPER = 0xFFFFFFFFu;
        private const uint CALLBACK_NULL = 0u;
        private const uint WHDR_BEGINLOOP = 0x00000004;
        private const uint WHDR_ENDLOOP = 0x00000008;

        [StructLayout(LayoutKind.Sequential)]
        private struct WAVEFORMATEX
        {
            public ushort wFormatTag; public ushort nChannels; public uint nSamplesPerSec;
            public uint nAvgBytesPerSec; public ushort nBlockAlign; public ushort wBitsPerSample; public ushort cbSize;
        }

        [StructLayout(LayoutKind.Sequential)]
        private struct WAVEHDR
        {
            public IntPtr lpData; public uint dwBufferLength; public uint dwBytesRecorded;
            public IntPtr dwUser; public uint dwFlags; public uint dwLoops; public IntPtr lpNext; public IntPtr reserved;
        }

        private IntPtr hWaveOut = IntPtr.Zero;
        private IntPtr pcmDataPtr = IntPtr.Zero;
        private IntPtr waveHdrPtr = IntPtr.Zero;
        private GCHandle pcmPin;
        private IntPtr introDataPtr = IntPtr.Zero;
        private IntPtr introHdrPtr = IntPtr.Zero;
        private GCHandle introPin;
        private short[] pcmSamples;
        private short[] pcmOriginal;
        private short[] introSamples;
        private short[] introOriginal;
        private float currentVolume = 1f;
        private int lastVolumeApplyTick = -100000;
        private string currentFile;

        public bool IsOpen { get; private set; }
        public bool IsPausedByGame;
        public bool IsPausedByFocus;

        public void PlayIntroThenLoop(string introPath, string loopPath, bool loop, float volume)
        {
            if (currentFile == introPath && IsOpen) return;
            Stop();
            currentVolume = volume;
            byte[] introPcm, loopPcm;
            WAVEFORMATEX introFmt, loopFmt;
            if (!ReadWav(introPath, out introPcm, out introFmt))
            {
                DynamicMusicPlugin.Logger.LogWarning("Failed to read intro WAV: " + introPath);
                return;
            }
            if (!ReadWav(loopPath, out loopPcm, out loopFmt))
            {
                DynamicMusicPlugin.Logger.LogWarning("Failed to read loop WAV: " + loopPath);
                return;
            }
            if (introFmt.nSamplesPerSec != loopFmt.nSamplesPerSec || introFmt.nChannels != loopFmt.nChannels || introFmt.wBitsPerSample != loopFmt.wBitsPerSample)
            {
                DynamicMusicPlugin.Logger.LogWarning("Intro and loop WAV formats differ; playing loop only.");
                Play(loopPath, loop, volume);
                return;
            }
            try
            {
                pcmSamples = ToShorts(loopPcm);
                pcmOriginal = (short[])pcmSamples.Clone();
                pcmPin = GCHandle.Alloc(pcmSamples, GCHandleType.Pinned);
                pcmDataPtr = pcmPin.AddrOfPinnedObject();
                introSamples = ToShorts(introPcm);
                introOriginal = (short[])introSamples.Clone();
                introPin = GCHandle.Alloc(introSamples, GCHandleType.Pinned);
                introDataPtr = introPin.AddrOfPinnedObject();
                uint err = waveOutOpen(out hWaveOut, WAVE_MAPPER, ref loopFmt, IntPtr.Zero, IntPtr.Zero, CALLBACK_NULL);
                if (err != 0) { DynamicMusicPlugin.Logger.LogWarning("waveOutOpen failed: " + err); Cleanup(); return; }
                uint hdrSize = (uint)Marshal.SizeOf(typeof(WAVEHDR));
                introHdrPtr = Marshal.AllocHGlobal((int)hdrSize);
                WAVEHDR ih = new WAVEHDR();
                ih.lpData = introDataPtr; ih.dwBufferLength = (uint)(introSamples.Length * 2);
                ih.dwFlags = 0u; ih.dwLoops = 0u;
                Marshal.StructureToPtr(ih, introHdrPtr, false);
                waveOutPrepareHeader(hWaveOut, introHdrPtr, hdrSize);
                waveOutWrite(hWaveOut, introHdrPtr, hdrSize);
                waveHdrPtr = Marshal.AllocHGlobal((int)hdrSize);
                WAVEHDR lh = new WAVEHDR();
                lh.lpData = pcmDataPtr; lh.dwBufferLength = (uint)(pcmSamples.Length * 2);
                lh.dwFlags = loop ? (WHDR_BEGINLOOP | WHDR_ENDLOOP) : 0u;
                lh.dwLoops = loop ? 0xFFFFFFFFu : 0u;
                Marshal.StructureToPtr(lh, waveHdrPtr, false);
                waveOutPrepareHeader(hWaveOut, waveHdrPtr, hdrSize);
                waveOutWrite(hWaveOut, waveHdrPtr, hdrSize);
                ApplyVolume();
                IsOpen = true; IsPausedByGame = false; IsPausedByFocus = false; currentFile = introPath;
                DynamicMusicPlugin.Logger.LogInfo("Now playing intro (once) then loop: " + introPath + " -> " + loopPath);
            }
            catch (Exception e) { DynamicMusicPlugin.Logger.LogWarning("WavePlayer error: " + e.Message); Cleanup(); }
        }

        public void Play(string path, bool loop, float volume)
        {
            if (currentFile == path && IsOpen) return;
            Stop();
            currentVolume = volume;
            byte[] pcm; WAVEFORMATEX fmt;
            if (!ReadWav(path, out pcm, out fmt)) { DynamicMusicPlugin.Logger.LogWarning("Failed to read WAV: " + path); return; }
            try
            {
                pcmSamples = ToShorts(pcm);
                pcmOriginal = (short[])pcmSamples.Clone();
                pcmPin = GCHandle.Alloc(pcmSamples, GCHandleType.Pinned);
                pcmDataPtr = pcmPin.AddrOfPinnedObject();
                uint err = waveOutOpen(out hWaveOut, WAVE_MAPPER, ref fmt, IntPtr.Zero, IntPtr.Zero, CALLBACK_NULL);
                if (err != 0) { DynamicMusicPlugin.Logger.LogWarning("waveOutOpen failed: " + err); Cleanup(); return; }
                waveHdrPtr = Marshal.AllocHGlobal(Marshal.SizeOf(typeof(WAVEHDR)));
                WAVEHDR hdr = new WAVEHDR();
                hdr.lpData = pcmDataPtr; hdr.dwBufferLength = (uint)(pcmSamples.Length * 2);
                hdr.dwFlags = loop ? (WHDR_BEGINLOOP | WHDR_ENDLOOP) : 0u;
                hdr.dwLoops = loop ? 0xFFFFFFFFu : 0u;
                Marshal.StructureToPtr(hdr, waveHdrPtr, false);
                waveOutPrepareHeader(hWaveOut, waveHdrPtr, (uint)Marshal.SizeOf(typeof(WAVEHDR)));
                waveOutWrite(hWaveOut, waveHdrPtr, (uint)Marshal.SizeOf(typeof(WAVEHDR)));
                ApplyVolume();
                IsOpen = true; IsPausedByGame = false; IsPausedByFocus = false; currentFile = path;
                DynamicMusicPlugin.Logger.LogInfo("Now playing: " + path + (loop ? " (loop)" : " (once)"));
            }
            catch (Exception e) { DynamicMusicPlugin.Logger.LogWarning("WavePlayer error: " + e.Message); Cleanup(); }
        }

        public void Stop() { Cleanup(); currentFile = null; IsOpen = false; IsPausedByGame = false; IsPausedByFocus = false; }
        public void Pause() { if (IsOpen && hWaveOut != IntPtr.Zero) waveOutPause(hWaveOut); }
        public void Resume() { if (IsOpen && hWaveOut != IntPtr.Zero) waveOutRestart(hWaveOut); }

        public void SetVolume(float v)
        {
            currentVolume = Mathf.Clamp01(v);
            int now = Environment.TickCount;
            if (now - lastVolumeApplyTick < 150) return;
            lastVolumeApplyTick = now;
            ApplyVolume();
        }

        private void ApplyVolume()
        {
            ScaleBuffer(pcmSamples, pcmOriginal, currentVolume);
            ScaleBuffer(introSamples, introOriginal, currentVolume);
        }

        private static void ScaleBuffer(short[] target, short[] source, float gain)
        {
            if (target == null || source == null || target.Length == 0) return;
            int n = Math.Min(target.Length, source.Length);
            if (gain >= 0.999f)
            {
                Buffer.BlockCopy(source, 0, target, 0, n * 2);
                return;
            }
            for (int i = 0; i < n; i++)
                target[i] = (short)(source[i] * gain);
        }

        private static short[] ToShorts(byte[] pcm)
        {
            short[] s = new short[pcm.Length / 2];
            Buffer.BlockCopy(pcm, 0, s, 0, pcm.Length & ~1);
            return s;
        }

        private void Cleanup()
        {
            try
            {
                if (hWaveOut != IntPtr.Zero)
                {
                    waveOutReset(hWaveOut);
                    uint hdrSize = (uint)Marshal.SizeOf(typeof(WAVEHDR));
                    if (waveHdrPtr != IntPtr.Zero) { waveOutUnprepareHeader(hWaveOut, waveHdrPtr, hdrSize); Marshal.FreeHGlobal(waveHdrPtr); waveHdrPtr = IntPtr.Zero; }
                    if (introHdrPtr != IntPtr.Zero) { waveOutUnprepareHeader(hWaveOut, introHdrPtr, hdrSize); Marshal.FreeHGlobal(introHdrPtr); introHdrPtr = IntPtr.Zero; }
                    waveOutClose(hWaveOut); hWaveOut = IntPtr.Zero;
                }
                if (pcmPin.IsAllocated) pcmPin.Free();
                if (introPin.IsAllocated) introPin.Free();
                pcmDataPtr = IntPtr.Zero;
                introDataPtr = IntPtr.Zero;
                pcmSamples = null; pcmOriginal = null; introSamples = null; introOriginal = null;
            }
            catch { }
        }

        public void Dispose() { Stop(); }

        private static bool ReadWav(string path, out byte[] pcm, out WAVEFORMATEX fmt)
        {
            pcm = null; fmt = new WAVEFORMATEX();
            using (FileStream fs = File.OpenRead(path))
            using (BinaryReader br = new BinaryReader(fs))
            {
                if (new string(br.ReadChars(4)) != "RIFF") return false; br.ReadInt32();
                if (new string(br.ReadChars(4)) != "WAVE") return false;
                while (true)
                {
                    string chunkId; try { chunkId = new string(br.ReadChars(4)); } catch { return false; }
                    uint size = br.ReadUInt32();
                    if (chunkId == "fmt ") { fmt.wFormatTag = br.ReadUInt16(); fmt.nChannels = br.ReadUInt16(); fmt.nSamplesPerSec = br.ReadUInt32(); fmt.nAvgBytesPerSec = br.ReadUInt32(); fmt.nBlockAlign = br.ReadUInt16(); fmt.wBitsPerSample = br.ReadUInt16(); if (size > 16) br.ReadBytes((int)(size - 16)); }
                    else if (chunkId == "data") { pcm = br.ReadBytes((int)size); return pcm != null && pcm.Length > 0; }
                    else br.ReadBytes((int)size);
                }
            }
        }
    }

    internal static class MiniJson
    {
        private static int pos;
        private static string src;

        public static object Parse(string json) { src = json; pos = 0; return ParseValue(); }
        private static void SkipWs() { while (pos < src.Length && char.IsWhiteSpace(src[pos])) pos++; }

        private static object ParseValue()
        {
            SkipWs(); if (pos >= src.Length) return null;
            char c = src[pos];
            if (c == '{') return ParseObj();
            if (c == '[') return ParseArr();
            if (c == '"') return ParseStr();
            if (c == 't' || c == 'f') return ParseBool();
            if (c == 'n') { pos += 4; return null; }
            return ParseNum();
        }

        private static Dictionary<string, object> ParseObj()
        {
            var d = new Dictionary<string, object>(); pos++; SkipWs();
            if (pos < src.Length && src[pos] == '}') { pos++; return d; }
            while (pos < src.Length)
            {
                SkipWs(); string key = ParseStr(); SkipWs();
                if (pos < src.Length && src[pos] == ':') pos++;
                d[key] = ParseValue(); SkipWs();
                if (pos < src.Length && src[pos] == ',') { pos++; continue; }
                if (pos < src.Length && src[pos] == '}') { pos++; break; }
                break;
            }
            return d;
        }

        private static List<object> ParseArr()
        {
            var l = new List<object>(); pos++; SkipWs();
            if (pos < src.Length && src[pos] == ']') { pos++; return l; }
            while (pos < src.Length)
            {
                l.Add(ParseValue()); SkipWs();
                if (pos < src.Length && src[pos] == ',') { pos++; continue; }
                if (pos < src.Length && src[pos] == ']') { pos++; break; }
                break;
            }
            return l;
        }

        private static string ParseStr()
        {
            if (pos >= src.Length || src[pos] != '"') return ""; pos++;
            var sb = new System.Text.StringBuilder();
            while (pos < src.Length)
            {
                char c = src[pos];
                if (c == '"') { pos++; break; }
                if (c == '\\') { pos++; if (pos >= src.Length) break; char e = src[pos]; if (e == 'n') sb.Append('\n'); else if (e == 't') sb.Append('\t'); else if (e == 'r') sb.Append('\r'); else if (e == 'u' && pos + 4 < src.Length) { sb.Append((char)Convert.ToInt32(src.Substring(pos + 1, 4), 16)); pos += 4; } else sb.Append(e); }
                else sb.Append(c);
                pos++;
            }
            return sb.ToString();
        }

        private static bool ParseBool()
        {
            if (pos + 4 <= src.Length && src.Substring(pos, 4) == "true") { pos += 4; return true; }
            if (pos + 5 <= src.Length && src.Substring(pos, 5) == "false") { pos += 5; return false; }
            return false;
        }

        private static object ParseNum()
        {
            int start = pos;
            while (pos < src.Length && (char.IsDigit(src[pos]) || src[pos] == '.' || src[pos] == '-' || src[pos] == '+' || src[pos] == 'e' || src[pos] == 'E')) pos++;
            double d; return double.TryParse(src.Substring(start, pos - start), NumberStyles.Any, CultureInfo.InvariantCulture, out d) ? d : 0.0;
        }
    }
}
