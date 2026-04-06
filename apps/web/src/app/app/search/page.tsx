"use client";

import { useState } from "react";
import { Search as SearchIcon, FileText, MessageSquare, Code, Users } from "lucide-react";
import { context, type ContextEntity } from "@/lib/api";

const typeIcons: Record<string, typeof FileText> = {
  document: FileText,
  message: MessageSquare,
  task: Code,
  person: Users,
};

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<ContextEntity[]>([]);
  const [searching, setSearching] = useState(false);
  const [searched, setSearched] = useState(false);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setSearching(true);
    setSearched(true);
    try {
      const res = await context.search(query.trim());
      setResults(res.results);
    } catch (err) {
      console.error(err);
    } finally {
      setSearching(false);
    }
  };

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold text-white mb-6">Search Context</h1>

      <form onSubmit={handleSearch} className="flex gap-3 mb-8">
        <div className="relative flex-1">
          <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search across all connected tools..."
            className="w-full bg-white/5 border border-white/10 rounded-xl pl-10 pr-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-[var(--accent)] text-sm"
          />
        </div>
        <button
          type="submit"
          disabled={searching}
          className="bg-[var(--accent)] hover:bg-[var(--accent)]/80 text-white rounded-xl px-6 py-3 text-sm font-medium transition-colors disabled:opacity-50"
        >
          {searching ? "Searching..." : "Search"}
        </button>
      </form>

      {/* Results */}
      <div className="space-y-3">
        {results.map((entity) => {
          const Icon = typeIcons[entity.entity_type] || FileText;
          return (
            <div
              key={entity.id}
              className="glass-card p-4 hover:border-[var(--accent)]/30 transition-colors"
            >
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-[var(--accent)]/10 flex items-center justify-center shrink-0">
                  <Icon className="w-4 h-4 text-[var(--accent)]" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="text-sm font-medium text-white truncate">
                      {entity.title}
                    </h3>
                    <span className="text-xs px-2 py-0.5 rounded-full bg-white/5 text-gray-400">
                      {entity.entity_type}
                    </span>
                    {entity.relevance_score && (
                      <span className="text-xs text-gray-500">
                        {Math.round(entity.relevance_score * 100)}% match
                      </span>
                    )}
                  </div>
                  {entity.content && (
                    <p className="text-xs text-gray-400 line-clamp-2">
                      {entity.content}
                    </p>
                  )}
                  {entity.source_url && (
                    <a
                      href={entity.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-[var(--accent)] hover:underline mt-1 inline-block"
                    >
                      Open source →
                    </a>
                  )}
                </div>
              </div>
            </div>
          );
        })}

        {searched && !searching && results.length === 0 && (
          <div className="text-center text-gray-400 py-12">
            No results found for &ldquo;{query}&rdquo;
          </div>
        )}
      </div>
    </div>
  );
}
