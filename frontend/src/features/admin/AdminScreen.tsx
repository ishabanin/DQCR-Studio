import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import {
  fetchAdminMacros,
  fetchAdminRules,
  fetchAdminTemplate,
  listAdminTemplates,
  saveAdminRules,
  saveAdminTemplate,
  type AdminRuleItem,
  type AdminTemplateFolderRule,
} from "../../api/projects";
import { useUiStore } from "../../app/store/uiStore";
import CatalogPanel from "./CatalogPanel";

type AdminTab = "templates" | "rules" | "macros";

export default function AdminScreen() {
  const userRole = useUiStore((state) => state.userRole);
  const addToast = useUiStore((state) => state.addToast);
  const [tab, setTab] = useState<AdminTab>("templates");
  const [selectedTemplate, setSelectedTemplate] = useState("flx");
  const [templateContent, setTemplateContent] = useState("");
  const [folderRules, setFolderRules] = useState<AdminTemplateFolderRule[]>([]);
  const [rulesDraft, setRulesDraft] = useState<AdminRuleItem[]>([]);
  const [ruleTestSql, setRuleTestSql] = useState("select 1 as id");

  const templatesQuery = useQuery({
    queryKey: ["adminTemplates"],
    queryFn: listAdminTemplates,
    enabled: userRole === "admin",
  });

  const templateQuery = useQuery({
    queryKey: ["adminTemplate", selectedTemplate],
    queryFn: () => fetchAdminTemplate(selectedTemplate),
    enabled: userRole === "admin" && Boolean(selectedTemplate),
  });

  const rulesQuery = useQuery({
    queryKey: ["adminRules"],
    queryFn: fetchAdminRules,
    enabled: userRole === "admin",
  });

  const macrosQuery = useQuery({
    queryKey: ["adminMacros"],
    queryFn: fetchAdminMacros,
    enabled: userRole === "admin",
  });

  useEffect(() => {
    const first = templatesQuery.data?.[0]?.name;
    if (!selectedTemplate && first) setSelectedTemplate(first);
  }, [templatesQuery.data, selectedTemplate]);

  useEffect(() => {
    if (!templateQuery.data) return;
    setTemplateContent(templateQuery.data.content);
    setFolderRules(templateQuery.data.rules.folders);
  }, [templateQuery.data]);

  useEffect(() => {
    if (!rulesQuery.data) return;
    setRulesDraft(rulesQuery.data);
  }, [rulesQuery.data]);

  const saveTemplateMutation = useMutation({
    mutationFn: () =>
      saveAdminTemplate(selectedTemplate, {
        content: templateContent,
        rules: { folders: folderRules },
      }),
    onSuccess: () => addToast("Template saved", "success"),
    onError: () => addToast("Failed to save template", "error"),
  });

  const saveRulesMutation = useMutation({
    mutationFn: () => saveAdminRules(rulesDraft),
    onSuccess: (nextRules) => {
      setRulesDraft(nextRules);
      addToast("Rules saved", "success");
    },
    onError: () => addToast("Failed to save rules", "error"),
  });

  const inlineTestResults = useMemo(() => {
    const sample = ruleTestSql.toLowerCase();
    return rulesDraft.map((rule) => {
      const pattern = rule.pattern.trim();
      if (!pattern) return { id: rule.id, pass: true, reason: "No pattern" };
      let pass = false;
      try {
        pass = new RegExp(pattern, "i").test(sample);
      } catch {
        pass = sample.includes(pattern.toLowerCase());
      }
      return { id: rule.id, pass, reason: pass ? "Matched" : "No match" };
    });
  }, [rulesDraft, ruleTestSql]);

  if (userRole !== "admin") {
    return (
      <section className="workbench">
        <h1>Admin</h1>
        <p>Admin access required. Switch role to admin in top bar.</p>
      </section>
    );
  }

  return (
    <section className="workbench">
      <h1>Admin</h1>
      <CatalogPanel />
      <div className="admin-tabs">
        <button type="button" className={tab === "templates" ? "action-btn action-btn-primary" : "action-btn"} onClick={() => setTab("templates")}>
          Templates
        </button>
        <button type="button" className={tab === "rules" ? "action-btn action-btn-primary" : "action-btn"} onClick={() => setTab("rules")}>
          Rules
        </button>
        <button type="button" className={tab === "macros" ? "action-btn action-btn-primary" : "action-btn"} onClick={() => setTab("macros")}>
          Macros
        </button>
      </div>

      {tab === "templates" ? (
        <div className="admin-grid">
          <section className="admin-card">
            <h2>Template Manager</h2>
            <select value={selectedTemplate} onChange={(event) => setSelectedTemplate(event.target.value)}>
              {(templatesQuery.data ?? []).map((item) => (
                <option key={item.name} value={item.name}>
                  {item.name}
                </option>
              ))}
            </select>
            <textarea className="admin-textarea" value={templateContent} onChange={(event) => setTemplateContent(event.target.value)} />
            <button type="button" className="action-btn action-btn-primary" onClick={() => saveTemplateMutation.mutate()}>
              Save Template
            </button>
          </section>
          <section className="admin-card">
            <h2>rules.folders</h2>
            <div className="admin-list">
              {folderRules.map((item, index) => (
                <div key={`${item.name}-${index}`} className="admin-row">
                  <input
                    className="ui-input"
                    value={item.name}
                    onChange={(event) =>
                      setFolderRules((prev) => prev.map((row, i) => (i === index ? { ...row, name: event.target.value } : row)))
                    }
                  />
                  <input
                    className="ui-input"
                    value={item.materialized}
                    onChange={(event) =>
                      setFolderRules((prev) => prev.map((row, i) => (i === index ? { ...row, materialized: event.target.value } : row)))
                    }
                  />
                  <label className="admin-check">
                    <input
                      type="checkbox"
                      checked={item.enabled}
                      onChange={(event) =>
                        setFolderRules((prev) => prev.map((row, i) => (i === index ? { ...row, enabled: event.target.checked } : row)))
                      }
                    />
                    enabled
                  </label>
                </div>
              ))}
            </div>
            <button
              type="button"
              className="action-btn"
              onClick={() => setFolderRules((prev) => [...prev, { name: "new_folder", materialized: "insert_fc", enabled: true }])}
            >
              Add Folder Rule
            </button>
          </section>
        </div>
      ) : null}

      {tab === "rules" ? (
        <div className="admin-grid">
          <section className="admin-card">
            <h2>Rules Manager</h2>
            <div className="admin-list">
              {rulesDraft.map((rule, index) => (
                <div key={rule.id} className="admin-rule-card">
                  <input
                    className="ui-input"
                    value={rule.id}
                    onChange={(event) => setRulesDraft((prev) => prev.map((item, i) => (i === index ? { ...item, id: event.target.value } : item)))}
                  />
                  <input
                    className="ui-input"
                    value={rule.name}
                    onChange={(event) => setRulesDraft((prev) => prev.map((item, i) => (i === index ? { ...item, name: event.target.value } : item)))}
                  />
                  <select
                    value={rule.severity}
                    onChange={(event) =>
                      setRulesDraft((prev) =>
                        prev.map((item, i) => (i === index ? { ...item, severity: event.target.value as AdminRuleItem["severity"] } : item)),
                      )
                    }
                  >
                    <option value="pass">pass</option>
                    <option value="warning">warning</option>
                    <option value="error">error</option>
                  </select>
                  <input
                    className="ui-input"
                    value={rule.pattern}
                    onChange={(event) => setRulesDraft((prev) => prev.map((item, i) => (i === index ? { ...item, pattern: event.target.value } : item)))}
                  />
                  <label className="admin-check">
                    <input
                      type="checkbox"
                      checked={rule.enabled}
                      onChange={(event) => setRulesDraft((prev) => prev.map((item, i) => (i === index ? { ...item, enabled: event.target.checked } : item)))}
                    />
                    enabled
                  </label>
                </div>
              ))}
            </div>
            <button type="button" className="action-btn action-btn-primary" onClick={() => saveRulesMutation.mutate()}>
              Save Rules
            </button>
          </section>
          <section className="admin-card">
            <h2>Inline Rule Test</h2>
            <textarea className="admin-textarea" value={ruleTestSql} onChange={(event) => setRuleTestSql(event.target.value)} />
            <ul className="admin-list-plain">
              {inlineTestResults.map((item) => (
                <li key={item.id}>
                  <strong>{item.id}</strong>: {item.pass ? "pass" : "fail"} ({item.reason})
                </li>
              ))}
            </ul>
          </section>
        </div>
      ) : null}

      {tab === "macros" ? (
        <section className="admin-card">
          <h2>Macro Registry</h2>
          <ul className="admin-list-plain">
            {(macrosQuery.data ?? []).map((item) => (
              <li key={item.name}>
                <strong>{item.name}</strong> <span className="admin-muted">[{item.source}]</span> — {item.description}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </section>
  );
}
