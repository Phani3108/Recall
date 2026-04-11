"use client";

import { useState, useEffect } from "react";
import {
  Zap,
  Play,
  Copy,
  ArrowUpCircle,
  ArrowDownCircle,
  Globe,
  Lock,
  Plus,
  Loader2,
  Package,
  ChevronDown,
  ChevronUp,
  Clock,
  Wrench,
} from "lucide-react";
import {
  skills,
  type SkillItem,
  type BuiltinTemplate,
} from "@/lib/api";
import { useDemo } from "@/lib/demo";
import { demoSkills, demoBuiltinTemplates } from "@/lib/demo-data";

const triggerLabels: Record<string, string> = {
  scheduled: "Scheduled",
  on_pattern: "On Pattern",
  on_sync: "On Sync",
  manual: "Manual",
};

function TriggerBadge({ trigger }: { trigger: Record<string, unknown> }) {
  const type = (trigger.type as string) || "manual";
  return (
    <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-white/5 text-gray-400">
      <Clock className="w-3 h-3" />
      {triggerLabels[type] || type}
      {trigger.cron ? <span className="text-gray-500 ml-1 font-mono">{String(trigger.cron)}</span> : null}
      {trigger.pattern ? <span className="text-gray-500 ml-1">{String(trigger.pattern)}</span> : null}
    </span>
  );
}

function StepRow({ step, index }: { step: { tool: string; action: string; params: Record<string, unknown> }; index: number }) {
  return (
    <div className="flex items-center gap-3 py-2 pl-4 border-l-2 border-white/10">
      <span className="text-xs text-gray-500 w-5">{index + 1}.</span>
      <span className="text-xs font-medium text-[var(--accent)]">{step.tool}</span>
      <span className="text-xs text-gray-500">→</span>
      <span className="text-xs text-white">{step.action}</span>
      {Object.keys(step.params).length > 0 && (
        <span className="text-xs text-gray-500 truncate max-w-[200px]">
          ({Object.keys(step.params).join(", ")})
        </span>
      )}
    </div>
  );
}

function SkillCard({
  skill,
  onVote,
  onPublish,
  onExecute,
  onClone,
}: {
  skill: SkillItem;
  onVote: (id: string, dir: "up" | "down") => void;
  onPublish: (id: string, published: boolean) => void;
  onExecute: (id: string) => void;
  onClone: (id: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="glass-card p-5">
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="text-sm font-semibold text-white">{skill.name}</h3>
            {skill.is_builtin && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-[var(--accent)]/20 text-[var(--accent)]">Built-in</span>
            )}
            {skill.is_published ? (
              <Globe className="w-3.5 h-3.5 text-green-400" />
            ) : (
              <Lock className="w-3.5 h-3.5 text-gray-500" />
            )}
            <span className="text-[10px] text-gray-500">v{skill.version}</span>
          </div>
          <p className="text-xs text-gray-400 line-clamp-2">{skill.description}</p>
        </div>
        <div className="flex items-center gap-1 ml-3">
          <button onClick={() => onVote(skill.id, "up")} className="p-1 text-gray-500 hover:text-green-400 transition-colors">
            <ArrowUpCircle className="w-4 h-4" />
          </button>
          <span className="text-xs text-gray-400 min-w-[20px] text-center">{skill.upvotes - skill.downvotes}</span>
          <button onClick={() => onVote(skill.id, "down")} className="p-1 text-gray-500 hover:text-red-400 transition-colors">
            <ArrowDownCircle className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="flex items-center gap-3 mb-3">
        <TriggerBadge trigger={skill.trigger} />
        <span className="text-xs text-gray-500">{skill.execution_count} runs</span>
        <span className="text-xs text-gray-500">{skill.steps.length} steps</span>
      </div>

      {/* Expandable steps */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-300 mb-2"
      >
        {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
        {expanded ? "Hide steps" : "Show steps"}
      </button>

      {expanded && (
        <div className="mb-3 space-y-1">
          {skill.steps.map((step, i) => (
            <StepRow key={i} step={step} index={i} />
          ))}
        </div>
      )}

      <div className="flex items-center gap-2 pt-2 border-t border-white/5">
        <button
          onClick={() => onExecute(skill.id)}
          className="flex items-center gap-1.5 text-xs bg-[var(--accent)] hover:bg-[var(--accent)]/80 text-white rounded-lg px-3 py-1.5 transition-colors"
        >
          <Play className="w-3 h-3" /> Run
        </button>
        <button
          onClick={() => onClone(skill.id)}
          className="flex items-center gap-1.5 text-xs bg-white/5 hover:bg-white/10 text-gray-300 rounded-lg px-3 py-1.5 transition-colors"
        >
          <Copy className="w-3 h-3" /> Clone
        </button>
        <button
          onClick={() => onPublish(skill.id, !skill.is_published)}
          className="flex items-center gap-1.5 text-xs bg-white/5 hover:bg-white/10 text-gray-300 rounded-lg px-3 py-1.5 transition-colors ml-auto"
        >
          {skill.is_published ? <Lock className="w-3 h-3" /> : <Globe className="w-3 h-3" />}
          {skill.is_published ? "Unpublish" : "Publish"}
        </button>
      </div>
    </div>
  );
}

export default function SkillsPage() {
  const { isDemo, markBackendDown } = useDemo();
  const [skillList, setSkillList] = useState<SkillItem[]>([]);
  const [builtins, setBuiltins] = useState<BuiltinTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<"installed" | "templates">("installed");
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [creating, setCreating] = useState(false);

  const load = async () => {
    if (isDemo) {
      setSkillList(demoSkills);
      setBuiltins(demoBuiltinTemplates);
      setLoading(false);
      return;
    }
    try {
      const [s, b] = await Promise.all([
        skills.list(),
        skills.builtins().catch(() => demoBuiltinTemplates),
      ]);
      setSkillList(s);
      setBuiltins(b);
    } catch {
      markBackendDown();
      setSkillList(demoSkills);
      setBuiltins(demoBuiltinTemplates);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [isDemo]);

  const handleVote = async (id: string, dir: "up" | "down") => {
    if (isDemo) return;
    try {
      const res = await skills.vote(id, dir);
      setSkillList((prev) => prev.map((s) => (s.id === id ? { ...s, upvotes: res.upvotes, downvotes: res.downvotes } : s)));
    } catch {}
  };

  const handlePublish = async (id: string, publish: boolean) => {
    if (isDemo) {
      setSkillList((prev) => prev.map((s) => (s.id === id ? { ...s, is_published: publish } : s)));
      return;
    }
    try {
      const updated = publish ? await skills.publish(id) : await skills.unpublish(id);
      setSkillList((prev) => prev.map((s) => (s.id === id ? updated : s)));
    } catch {}
  };

  const handleExecute = async (id: string) => {
    if (isDemo) return;
    try {
      await skills.execute(id);
    } catch {}
  };

  const handleClone = async (id: string) => {
    if (isDemo) return;
    try {
      const cloned = await skills.clone(id);
      setSkillList((prev) => [cloned, ...prev]);
    } catch {}
  };

  const handleCreate = async () => {
    if (!newName.trim() || !newDesc.trim()) return;
    setCreating(true);
    try {
      if (isDemo) {
        setSkillList((prev) => [
          { id: `skill-${Date.now()}`, name: newName, description: newDesc, version: 1, is_builtin: false, is_published: false, execution_count: 0, upvotes: 0, downvotes: 0, steps: [], trigger: { type: "manual" }, created_at: new Date().toISOString() },
          ...prev,
        ]);
      } else {
        const created = await skills.create({ name: newName, description: newDesc, trigger: { type: "manual" } });
        setSkillList((prev) => [created, ...prev]);
      }
      setNewName("");
      setNewDesc("");
      setShowCreate(false);
    } catch {} finally {
      setCreating(false);
    }
  };

  const handleInstallBuiltin = async (name: string) => {
    if (isDemo) return;
    try {
      const installed = await skills.installBuiltin(name);
      setSkillList((prev) => [installed, ...prev]);
    } catch {}
  };

  if (loading) {
    return (
      <div className="p-6 flex justify-center">
        <Loader2 className="w-6 h-6 text-gray-400 animate-spin" />
      </div>
    );
  }

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Skills</h1>
          <p className="text-gray-400 text-sm mt-1">Reusable AI workflows that chain tool actions together.</p>
        </div>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="flex items-center gap-2 bg-[var(--accent)] hover:bg-[var(--accent)]/80 text-white rounded-lg px-4 py-2 text-sm transition-colors"
        >
          <Plus className="w-4 h-4" /> New Skill
        </button>
      </div>

      {/* Create form */}
      {showCreate && (
        <div className="glass-card p-5 mb-6">
          <h3 className="text-sm font-semibold text-white mb-3">Create Skill</h3>
          <div className="space-y-3">
            <input
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="Skill name"
              className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-[var(--accent)]"
            />
            <textarea
              value={newDesc}
              onChange={(e) => setNewDesc(e.target.value)}
              placeholder="What does this skill do?"
              rows={2}
              className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-[var(--accent)] resize-none"
            />
            <div className="flex gap-2">
              <button onClick={handleCreate} disabled={creating} className="bg-[var(--accent)] hover:bg-[var(--accent)]/80 text-white rounded-lg px-4 py-2 text-sm disabled:opacity-50">
                {creating ? "Creating..." : "Create"}
              </button>
              <button onClick={() => setShowCreate(false)} className="text-gray-400 hover:text-white text-sm">Cancel</button>
            </div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-white/5 rounded-lg p-1 w-fit">
        <button
          onClick={() => setTab("installed")}
          className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm transition-colors ${tab === "installed" ? "bg-[var(--accent)] text-white" : "text-gray-400 hover:text-white hover:bg-white/5"}`}
        >
          <Zap className="w-4 h-4" /> Installed ({skillList.length})
        </button>
        <button
          onClick={() => setTab("templates")}
          className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm transition-colors ${tab === "templates" ? "bg-[var(--accent)] text-white" : "text-gray-400 hover:text-white hover:bg-white/5"}`}
        >
          <Package className="w-4 h-4" /> Templates ({builtins.length})
        </button>
      </div>

      {/* Installed skills */}
      {tab === "installed" && (
        <div className="grid md:grid-cols-2 gap-4">
          {skillList.length === 0 ? (
            <div className="col-span-2 text-center text-gray-400 py-12">
              No skills yet. Create one or install from templates.
            </div>
          ) : (
            skillList.map((s) => (
              <SkillCard
                key={s.id}
                skill={s}
                onVote={handleVote}
                onPublish={handlePublish}
                onExecute={handleExecute}
                onClone={handleClone}
              />
            ))
          )}
        </div>
      )}

      {/* Builtin templates */}
      {tab === "templates" && (
        <div className="grid md:grid-cols-2 gap-4">
          {builtins.map((t) => {
            const installed = skillList.some((s) => s.name === t.name && s.is_builtin);
            return (
              <div key={t.name} className="glass-card p-5">
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <h3 className="text-sm font-semibold text-white">{t.name}</h3>
                    <p className="text-xs text-gray-400 mt-1">{t.description}</p>
                  </div>
                  <Wrench className="w-4 h-4 text-gray-500 shrink-0" />
                </div>
                <div className="flex items-center gap-3 mt-3">
                  <TriggerBadge trigger={t.trigger} />
                  <span className="text-xs text-gray-500">{t.steps.length} steps</span>
                </div>
                <button
                  onClick={() => handleInstallBuiltin(t.name)}
                  disabled={installed}
                  className={`mt-3 flex items-center gap-1.5 text-xs rounded-lg px-3 py-1.5 transition-colors ${
                    installed
                      ? "bg-green-400/10 text-green-400 cursor-default"
                      : "bg-[var(--accent)] hover:bg-[var(--accent)]/80 text-white"
                  }`}
                >
                  {installed ? "Installed" : "Install"}
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
