"use client";

const TEMPLATES = [
  { value: "", label: "Default" },
  { value: "empty", label: "Empty Board" },
  { value: "sprint", label: "Sprint Board" },
  { value: "bug_tracker", label: "Bug Tracker" },
  { value: "product_roadmap", label: "Product Roadmap" },
];

type TemplateSelectorProps = {
  value: string;
  onChange: (template: string) => void;
};

export const TemplateSelector = ({ value, onChange }: TemplateSelectorProps) => (
  <select
    value={value}
    onChange={(e) => onChange(e.target.value)}
    className="rounded-xl border border-[var(--stroke)] bg-white px-3 py-1.5 text-sm text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
  >
    {TEMPLATES.map((t) => (
      <option key={t.value} value={t.value}>
        {t.label}
      </option>
    ))}
  </select>
);
