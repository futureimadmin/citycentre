"use client";

import { useState, useRef, useEffect } from "react";
import {
  Send, Package, ShoppingCart, Truck, Users, Upload,
  Bot, User, CreditCard, MapPin, ClipboardList
} from "lucide-react";

type Message = {
  id: string;
  role: "user" | "agent" | "system";
  content: string;
  agentName?: string;
};

const TABS = [
  { id: "shop", label: "Shop", icon: ShoppingCart },
  { id: "cart", label: "Cart", icon: ClipboardList },
  { id: "offers", label: "Offers", icon: Package },
  { id: "loyalty", label: "Loyalty", icon: User },
  { id: "checkout", label: "Checkout", icon: CreditCard },
  { id: "orders", label: "Orders", icon: Truck },
  { id: "returns", label: "Returns", icon: Truck },
  { id: "inventory", label: "Inventory", icon: Package },
  { id: "partners", label: "Partners", icon: Users },
] as const;

export default function AgentCommerceHome() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      role: "system",
      content:
        "Welcome to Agent Commerce. Full domain: Catalogue → Cart → Offers → Loyalty → Recommendations → Order → Returns. Ask any agent.",
    },
  ]);
  const [input, setInput] = useState("");
  const [activeTab, setActiveTab] = useState<(typeof TABS)[number]["id"]>("shop");
  const [isLoading, setIsLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return;
    const userMsg: Message = { id: Date.now().toString(), role: "user", content: input };
    setMessages((m) => [...m, userMsg]);
    setInput("");
    setIsLoading(true);

    try {
      // Production: stream from Root Orchestrator Cloud Run / ADK endpoint
      await new Promise((r) => setTimeout(r, 700));
      const agentReply: Message = {
        id: (Date.now() + 1).toString(),
        role: "agent",
        agentName: "Commerce Orchestrator",
        content: `Received: "${userMsg.content}". Live system routes this through Inventory / Cart / Customer / Payment / Shipping / Fulfillment agents via ADK 2.0 + A2A.`,
      };
      setMessages((m) => [...m, agentReply]);
    } finally {
      setIsLoading(false);
    }
  };

  const quickPrompts: Record<string, string[]> = {
    shop: [
      "Show me running shoes",
      "What electronics do you have under $100?",
      "Tell me about the TrailDay Backpack",
    ],
    cart: [
      "Add AeroRun Pro Shoes to my cart",
      "What's in my cart?",
      "Remove headphones from cart",
    ],
    offers: [
      "Apply code WELCOME10",
      "What offers are available?",
      "Apply FREESHIP and SAVE15",
      "Create a 15% off Electronics offer",
    ],
    checkout: [
      "I want to checkout with code FOOT20",
      "My address is 123 Main St, Austin TX 78701",
      "Pay with card",
    ],
    orders: [
      "Where is my latest order?",
      "List my orders",
      "Track shipment",
    ],
    inventory: [
      "Upload new inventory",
      "How many SonicWave Headphones left?",
      "Search backpacks",
    ],
    partners: [
      "Register me as a sales partner",
      "Show my commissions",
    ],
    loyalty: [
      "What's my points balance?",
      "Redeem 500 points",
      "What are Gold tier benefits?",
    ],
    returns: [
      "I want to return my shoes – wrong size",
      "Status of my return",
      "Start a return for order ORD-XXXX",
    ],
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-indigo-950 text-slate-100">
      <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center">
              <Bot className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight">Agent Commerce</h1>
              <p className="text-xs text-slate-400">ADK 2.0 · Full E-Commerce Domain</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {TABS.map((t) => (
              <button
                key={t.id}
                onClick={() => setActiveTab(t.id)}
                className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs sm:text-sm transition ${
                  activeTab === t.id
                    ? "bg-indigo-600 text-white"
                    : "bg-slate-800 hover:bg-slate-700 text-slate-300"
                }`}
              >
                <t.icon className="w-3.5 h-3.5" />
                {t.label}
              </button>
            ))}
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Chat */}
        <div className="lg:col-span-2 flex flex-col h-[72vh] rounded-2xl border border-slate-800 bg-slate-900/60 overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-800 flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-sm font-medium">Agent Chat</span>
            <span className="text-xs text-slate-500 ml-auto">Root Orchestrator + Specialists</span>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.map((m) => (
              <div key={m.id} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                <div
                  className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm ${
                    m.role === "user"
                      ? "bg-indigo-600 text-white"
                      : m.role === "system"
                      ? "bg-slate-800 text-slate-300 border border-slate-700"
                      : "bg-slate-800 text-slate-100 border border-slate-700"
                  }`}
                >
                  {m.agentName && (
                    <div className="text-xs text-indigo-400 font-medium mb-1 flex items-center gap-1">
                      <Bot className="w-3 h-3" /> {m.agentName}
                    </div>
                  )}
                  {m.content}
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-slate-800 rounded-2xl px-4 py-3 text-sm text-slate-400">
                  Agents coordinating…
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          <div className="p-4 border-t border-slate-800">
            <div className="flex gap-2">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && sendMessage()}
                placeholder="Talk to agents… e.g. “Add shoes to cart and checkout”"
                className="flex-1 bg-slate-950 border border-slate-700 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
              <button
                onClick={sendMessage}
                disabled={isLoading}
                className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 rounded-xl px-4 py-2.5"
              >
                <Send className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>

        {/* Side panel */}
        <div className="space-y-4">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
            <h2 className="font-semibold mb-3 capitalize">{activeTab} actions</h2>
            <div className="space-y-2">
              {(quickPrompts[activeTab] || []).map((q) => (
                <button
                  key={q}
                  onClick={() => setInput(q)}
                  className="w-full text-left text-sm bg-slate-800 hover:bg-slate-700 rounded-lg px-3 py-2 transition"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>

          {activeTab === "inventory" && (
            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
              <h2 className="font-semibold flex items-center gap-2 mb-3">
                <Upload className="w-5 h-5 text-indigo-400" /> Inventory Upload
              </h2>
              <p className="text-sm text-slate-400 mb-4">
                CSV/JSON → Inventory Agent validates & commits.
              </p>
              <div className="border-2 border-dashed border-slate-700 rounded-xl p-6 text-center text-slate-500 hover:border-indigo-500 transition cursor-pointer text-sm">
                Drop file or click (sku,name,price,stock,category)
              </div>
            </div>
          )}

          {activeTab === "checkout" && (
            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5 text-sm text-slate-400 space-y-2">
              <p className="font-medium text-slate-300 flex items-center gap-2">
                <MapPin className="w-4 h-4" /> Checkout path
              </p>
              <ol className="list-decimal list-inside space-y-1 text-xs">
                <li>Customer + Address</li>
                <li>Shipping rates</li>
                <li>Create Order</li>
                <li>Payment</li>
                <li>Shipment + Dispatch</li>
                <li>Commit stock</li>
              </ol>
            </div>
          )}

          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4 text-xs text-slate-500">
            <p className="font-medium text-slate-400 mb-1">Agents online</p>
            <p>13 agents: Inventory · Cart · Customer · Offers · Loyalty · Recommendations · Payment · Shipping · Fulfillment · Returns · Partners · Shopper · Orchestrator</p>
          </div>
        </div>
      </main>
    </div>
  );
}
