import React, { useEffect, useState } from "react";
import { View, Text, Pressable, TextInput, SafeAreaView, ScrollView, Alert } from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { NavigationContainer } from "@react-navigation/native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";

const Tab = createBottomTabNavigator();

const DEFAULT_API = "http://localhost:8000";

async function getApiBase() {
  const v = await AsyncStorage.getItem("API_BASE");
  return v || DEFAULT_API;
}

async function setApiBase(v: string) {
  await AsyncStorage.setItem("API_BASE", v);
}

async function apiGet(path: string) {
  const base = await getApiBase();
  const url = `${base}${path}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

function Banner({ ok, msg }: { ok: boolean; msg: string }) {
  if (ok) return null;
  return (
    <View style={{ backgroundColor: "#ffe3e3", padding: 10, borderRadius: 10, marginBottom: 12 }}>
      <Text style={{ color: "#b00020", fontWeight: "600" }}>{msg}</Text>
    </View>
  );
}

function GeneratorScreen() {
  const [online, setOnline] = useState(true);
  const [topic, setTopic] = useState("");
  const [status, setStatus] = useState("Ready");

  const ping = async () => {
    try {
      await apiGet("/api");
      setOnline(true);
    } catch {
      setOnline(false);
    }
  };

  useEffect(() => {
    ping();
  }, []);

  return (
    <SafeAreaView style={{ flex: 1, padding: 16 }}>
      <Banner ok={online} msg={"Backend offline. Check API URL in Accounts tab → Settings."} />
      <Text style={{ fontSize: 22, fontWeight: "700", marginBottom: 10 }}>Generator</Text>

      <Text style={{ marginBottom: 6 }}>Topic</Text>
      <TextInput
        value={topic}
        onChangeText={setTopic}
        placeholder="Enter a topic"
        style={{
          borderWidth: 1,
          borderColor: "#ddd",
          borderRadius: 10,
          padding: 12,
          marginBottom: 12,
        }}
      />

      <Pressable
        onPress={async () => {
          try {
            setStatus("Calling backend...");
            await ping();
            if (!online) throw new Error("Backend offline");
            // Adjust endpoint later to your exact backend routes
            const data = await apiGet("/api");
            setStatus(`Backend OK: ${data?.status || "running"}`);
          } catch (e: any) {
            setStatus(`Error: ${e.message}`);
            setOnline(false);
          }
        }}
        style={{
          backgroundColor: "#0B74DE",
          padding: 12,
          borderRadius: 10,
          alignItems: "center",
        }}
      >
        <Text style={{ color: "white", fontWeight: "700" }}>Test Backend</Text>
      </Pressable>

      <Text style={{ marginTop: 12, color: "#444" }}>{status}</Text>
    </SafeAreaView>
  );
}

function QueueScreen() {
  return (
    <SafeAreaView style={{ flex: 1, padding: 16 }}>
      <Text style={{ fontSize: 22, fontWeight: "700", marginBottom: 10 }}>Queue</Text>
      <Text>Next: connect to /api/jobs and show running/completed jobs.</Text>
    </SafeAreaView>
  );
}

function LibraryScreen() {
  return (
    <SafeAreaView style={{ flex: 1, padding: 16 }}>
      <Text style={{ fontSize: 22, fontWeight: "700", marginBottom: 10 }}>Library</Text>
      <Text>Next: connect to /api/library/videos and show videos.</Text>
    </SafeAreaView>
  );
}

function AccountsScreen() {
  const [apiBase, setLocalApiBase] = useState(DEFAULT_API);

  useEffect(() => {
    (async () => setLocalApiBase(await getApiBase()))();
  }, []);

  return (
    <SafeAreaView style={{ flex: 1, padding: 16 }}>
      <ScrollView>
        <Text style={{ fontSize: 22, fontWeight: "700", marginBottom: 10 }}>Accounts</Text>

        <Text style={{ fontWeight: "700", marginBottom: 6 }}>Settings: Backend API URL</Text>
        <Text style={{ color: "#444", marginBottom: 8 }}>
          Use your LAN IP (same WiFi) or Cloudflare tunnel URL.
        </Text>

        <TextInput
          value={apiBase}
          onChangeText={setLocalApiBase}
          placeholder="http://192.168.x.x:8000 OR https://xxxx.trycloudflare.com"
          autoCapitalize="none"
          style={{
            borderWidth: 1,
            borderColor: "#ddd",
            borderRadius: 10,
            padding: 12,
            marginBottom: 12,
          }}
        />

        <Pressable
          onPress={async () => {
            await setApiBase(apiBase.trim());
            Alert.alert("Saved", `API Base set to:\n${apiBase.trim()}`);
          }}
          style={{
            backgroundColor: "#111",
            padding: 12,
            borderRadius: 10,
            alignItems: "center",
            marginBottom: 10,
          }}
        >
          <Text style={{ color: "white", fontWeight: "700" }}>Save</Text>
        </Pressable>

        <Pressable
          onPress={async () => {
            try {
              const data = await apiGet("/api");
              Alert.alert("Connected", JSON.stringify(data, null, 2));
            } catch (e: any) {
              Alert.alert("Failed", e.message);
            }
          }}
          style={{
            backgroundColor: "#0B74DE",
            padding: 12,
            borderRadius: 10,
            alignItems: "center",
          }}
        >
          <Text style={{ color: "white", fontWeight: "700" }}>Test Connection</Text>
        </Pressable>
      </ScrollView>
    </SafeAreaView>
  );
}

export default function App() {
  return (
    <NavigationContainer>
      <Tab.Navigator screenOptions={{ headerShown: false }}>
        <Tab.Screen name="Generator" component={GeneratorScreen} />
        <Tab.Screen name="Queue" component={QueueScreen} />
        <Tab.Screen name="Library" component={LibraryScreen} />
        <Tab.Screen name="Accounts" component={AccountsScreen} />
      </Tab.Navigator>
    </NavigationContainer>
  );
}
