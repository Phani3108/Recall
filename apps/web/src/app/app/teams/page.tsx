"use client";

import { useState, useEffect } from "react";
import {
  Users,
  Plus,
  Loader2,
  Crown,
  UserPlus,
  UserMinus,
  Trash2,
  ChevronDown,
  ChevronRight,
} from "lucide-react";
import { teams as teamsApi, type TeamItem, type TeamMemberItem } from "@/lib/api";
import { useDemo } from "@/lib/demo";
import { demoTeams } from "@/lib/demo-data";

/* ── Create Team Dialog ── */

function CreateTeamForm({ onCreated }: { onCreated: () => void }) {
  const { isDemo } = useDemo();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [desc, setDesc] = useState("");
  const [saving, setSaving] = useState(false);

  const submit = async () => {
    if (!name.trim()) return;
    setSaving(true);
    try {
      if (!isDemo) {
        await teamsApi.create({ name: name.trim(), description: desc.trim() || undefined, slug: name.trim().toLowerCase().replace(/\s+/g, "-") });
      }
      onCreated();
      setName("");
      setDesc("");
      setOpen(false);
    } finally {
      setSaving(false);
    }
  };

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="flex items-center gap-2 px-4 py-2 bg-[var(--accent)] text-black rounded-lg text-sm font-medium hover:opacity-90 transition-opacity"
      >
        <Plus className="w-4 h-4" /> New Team
      </button>
    );
  }

  return (
    <div className="glass-card p-4 space-y-3">
      <input
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="Team name"
        className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-[var(--accent)]"
      />
      <input
        value={desc}
        onChange={(e) => setDesc(e.target.value)}
        placeholder="Description (optional)"
        className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-[var(--accent)]"
      />
      <div className="flex gap-2">
        <button
          onClick={submit}
          disabled={saving || !name.trim()}
          className="px-4 py-1.5 bg-[var(--accent)] text-black rounded-lg text-sm font-medium disabled:opacity-50"
        >
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : "Create"}
        </button>
        <button
          onClick={() => setOpen(false)}
          className="px-4 py-1.5 text-gray-400 text-sm hover:text-white"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

/* ── Team Card ── */

function TeamCard({
  team,
  onDeleted,
}: {
  team: TeamItem;
  onDeleted: () => void;
}) {
  const { isDemo } = useDemo();
  const [expanded, setExpanded] = useState(false);
  const [members, setMembers] = useState<TeamMemberItem[]>([]);
  const [loadingMembers, setLoadingMembers] = useState(false);
  const [addEmail, setAddEmail] = useState("");

  const loadMembers = async () => {
    if (isDemo) {
      setMembers([
        { id: "m1", user_id: "u1", user_name: "Alex Chen", user_email: "alex@acme.dev", role: "lead", joined_at: team.created_at },
        { id: "m2", user_id: "u2", user_name: "Sara Kim", user_email: "sara@acme.dev", role: "member", joined_at: team.created_at },
      ]);
      return;
    }
    setLoadingMembers(true);
    try {
      const m = await teamsApi.members(team.id);
      setMembers(m);
    } finally {
      setLoadingMembers(false);
    }
  };

  const toggle = () => {
    const next = !expanded;
    setExpanded(next);
    if (next && members.length === 0) loadMembers();
  };

  const addMember = async () => {
    if (!addEmail.trim()) return;
    if (!isDemo) await teamsApi.addMember(team.id, addEmail.trim());
    setAddEmail("");
    loadMembers();
  };

  const removeMember = async (uid: string) => {
    if (!isDemo) await teamsApi.removeMember(team.id, uid);
    loadMembers();
  };

  const deleteTeam = async () => {
    if (!isDemo) await teamsApi.delete(team.id);
    onDeleted();
  };

  return (
    <div className="glass-card overflow-hidden">
      <div
        className="flex items-center gap-4 p-4 cursor-pointer hover:bg-white/[0.02] transition-colors"
        onClick={toggle}
      >
        <div className="w-10 h-10 rounded-lg bg-[var(--accent)]/20 flex items-center justify-center text-[var(--accent)] font-bold text-lg">
          {team.name.charAt(0)}
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium text-white">{team.name}</div>
          {team.description && (
            <div className="text-xs text-gray-500 truncate">{team.description}</div>
          )}
        </div>
        <span className="text-xs text-gray-500">{team.member_count} members</span>
        {expanded ? (
          <ChevronDown className="w-4 h-4 text-gray-500" />
        ) : (
          <ChevronRight className="w-4 h-4 text-gray-500" />
        )}
      </div>

      {expanded && (
        <div className="border-t border-white/5 p-4 space-y-3">
          {loadingMembers ? (
            <div className="flex items-center gap-2 text-gray-400 text-xs">
              <Loader2 className="w-3 h-3 animate-spin" /> Loading members…
            </div>
          ) : (
            <div className="space-y-2">
              {members.map((m) => (
                <div key={m.id} className="flex items-center gap-3">
                  <div className="w-7 h-7 rounded-full bg-white/10 flex items-center justify-center text-xs text-white">
                    {m.user_name?.charAt(0) || m.user_email.charAt(0).toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <span className="text-sm text-white">{m.user_name || m.user_email}</span>
                    {m.role === "lead" && (
                      <Crown className="inline w-3 h-3 ml-1 text-yellow-400" />
                    )}
                  </div>
                  <span className="text-[10px] text-gray-600">{m.user_email}</span>
                  {m.role !== "lead" && (
                    <button
                      onClick={() => removeMember(m.user_id)}
                      className="text-gray-600 hover:text-red-400 transition-colors"
                      title="Remove member"
                    >
                      <UserMinus className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* add member */}
          <div className="flex gap-2 pt-2">
            <input
              value={addEmail}
              onChange={(e) => setAddEmail(e.target.value)}
              placeholder="Add by email…"
              className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-[var(--accent)]"
              onKeyDown={(e) => e.key === "Enter" && addMember()}
            />
            <button
              onClick={addMember}
              disabled={!addEmail.trim()}
              className="px-3 py-1.5 bg-[var(--accent)]/20 text-[var(--accent)] rounded-lg text-xs disabled:opacity-50"
            >
              <UserPlus className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* delete */}
          <button
            onClick={deleteTeam}
            className="flex items-center gap-1.5 text-xs text-gray-600 hover:text-red-400 transition-colors mt-2"
          >
            <Trash2 className="w-3 h-3" /> Delete team
          </button>
        </div>
      )}
    </div>
  );
}

/* ── main ── */

export default function TeamsPage() {
  const { isDemo } = useDemo();
  const [loading, setLoading] = useState(true);
  const [teamList, setTeamList] = useState<TeamItem[]>([]);

  const load = async () => {
    setLoading(true);
    try {
      if (isDemo) {
        setTeamList(demoTeams);
      } else {
        const t = await teamsApi.list();
        setTeamList(t);
      }
    } catch {
      setTeamList(demoTeams);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [isDemo]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full text-gray-400">
        <Loader2 className="w-5 h-5 animate-spin mr-2" /> Loading teams…
      </div>
    );
  }

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Users className="w-6 h-6 text-[var(--accent)]" /> Teams
          </h1>
          <p className="text-sm text-gray-400 mt-1">Manage teams and membership.</p>
        </div>
        <CreateTeamForm onCreated={load} />
      </div>

      {teamList.length === 0 ? (
        <div className="glass-card p-12 text-center">
          <Users className="w-8 h-8 text-gray-600 mx-auto mb-2" />
          <div className="text-gray-400 text-sm">No teams yet. Create one to get started.</div>
        </div>
      ) : (
        <div className="space-y-3">
          {teamList.map((t) => (
            <TeamCard key={t.id} team={t} onDeleted={load} />
          ))}
        </div>
      )}
    </div>
  );
}
