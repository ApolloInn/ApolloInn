const SKILLS = [
  { icon: "code", name: "Code Assistant", status: "enabled" as const, count: 24, desc: "Project scaffolding, code review, debugging, TDD" },
  { icon: "travel_explore", name: "Web Research", status: "enabled" as const, count: 16, desc: "Deep research, fact-checking, translation" },
  { icon: "cloud", name: "DevOps", status: "enabled" as const, count: 17, desc: "Docker, deployment, Kubernetes, CI/CD" },
  { icon: "database", name: "Data Processing", status: "enabled" as const, count: 18, desc: "CSV, JSON, SQL, statistics, scraping" },
  { icon: "folder_open", name: "File Management", status: "enabled" as const, count: 8, desc: "Organize, batch rename, search, compress" },
  { icon: "description", name: "Document", status: "enabled" as const, count: 12, desc: "PDF, README, API docs, diagrams" },
  { icon: "shield", name: "Security", status: "enabled" as const, count: 10, desc: "Audit, secret scan, OWASP, penetration" },
  { icon: "edit_note", name: "Writing", status: "enabled" as const, count: 12, desc: "Blog, copywriting, social media, summaries" },
  { icon: "school", name: "Learning", status: "enabled" as const, count: 12, desc: "Explain concepts, quizzes, mind maps" },
  { icon: "web", name: "Frontend", status: "enabled" as const, count: 10, desc: "React, Next.js, Vue, Tailwind, UI audit" },
  { icon: "phone_android", name: "Mobile", status: "needs-config" as const, count: 6, desc: "iOS, Android, React Native, Flutter" },
  { icon: "cloud_queue", name: "Cloud", status: "needs-config" as const, count: 9, desc: "AWS, Azure, GCP, serverless, CDN" },
  { icon: "smart_toy", name: "AI & ML", status: "enabled" as const, count: 6, desc: "Prompt engineering, RAG, evaluation" },
  { icon: "calculate", name: "Math", status: "enabled" as const, count: 4, desc: "Solve equations, unit conversion, plots" },
  { icon: "home", name: "Smart Home", status: "disabled" as const, count: 6, desc: "Home Assistant, lights, thermostat" },
  { icon: "fitness_center", name: "Health", status: "disabled" as const, count: 8, desc: "Workout plans, nutrition, sleep tracking" },
];

const STATUS_LABEL: Record<string, string> = {
  enabled: "Enabled",
  "needs-config": "Needs Config",
  disabled: "Disabled",
};

export function SkillsView() {
  return (
    <>
      <div className="chat-header">
        <div className="chat-header-left">
          <span className="material-symbols-rounded" style={{ color: "var(--color-primary)" }}>psychology</span>
          <span className="chat-header-title">Skill Center — {SKILLS.reduce((a, s) => a + s.count, 0)} Skills</span>
        </div>
      </div>

      <div className="skills-grid">
        {SKILLS.map((s) => (
          <div key={s.name} className="skill-card">
            <div className="skill-card-icon">
              <span className="material-symbols-rounded">{s.icon}</span>
            </div>
            <div className="skill-card-name">{s.name}</div>
            <div className={`skill-card-status ${s.status}`}>
              {STATUS_LABEL[s.status]}{s.status === "enabled" ? ` · ${s.count} skills` : ""}
            </div>
            <div className="skill-card-desc">{s.desc}</div>
          </div>
        ))}
      </div>
    </>
  );
}
