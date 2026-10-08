(function () {
  "use strict";
  var sdk = window.__HERMES_PLUGIN_SDK__, registry = window.__HERMES_PLUGINS__;
  if (!sdk || !registry) return;
  var R = sdk.React, h = R.createElement;
  var base = "/api/plugins/landmarksignal-launch";
  function api(path, init, task) { return sdk.fetchJSON(base + path + "?profile=jeeves&task=" + encodeURIComponent(task || "issue7-status-mapping"), init); }
  function IntakePanel() {
    var a = R.useState(false), busy = a[0], setBusy = a[1];
    var b = R.useState(null), result = b[0], setResult = b[1];
    var c = R.useState(""), error = c[0], setError = c[1];
    async function importQueue() {
      if (busy) return;
      setBusy(true); setError(""); setResult(null);
      try { setResult(await api("/github-intake", {method: "POST"})); }
      catch (err) { setError(String(err.message || err)); }
      finally { setBusy(false); }
    }
    return h("section", {style: {border: "1px solid #A9B7A4", padding: "16px", marginBottom: "16px", borderRadius: "8px"}},
      h("strong", null, "GitHub → Hermes Triage"),
      h("p", null, "Select issues in GitHub Project #3 using Queued for Jeeves, then import the batch here."),
      h("p", null, "Imports preserve original requirements and recorded GitHub dependencies. Specification and execution use the existing Kanban controls; this button starts neither."),
      h("button", {onClick: importQueue, disabled: busy, style: {padding: "8px 14px", cursor: "pointer"}}, busy ? "Reading GitHub and importing…" : "Import queued work"),
      h("a", {href: "/kanban?profile=jeeves&board=landmarksignal", style: {marginLeft: "16px"}}, "Open LandmarkSignal Kanban"),
      error ? h("p", {role: "alert"}, error) : null,
      result ? h("div", null,
        h("p", null, result.created.length + " imported · " + result.existing.length + " already linked · " + result.skipped.length + " need review"),
        result.created.map(function (item) { return h("p", {key: item.task_id}, h("a", {href: item.issue_url, target: "_blank", rel: "noopener noreferrer"}, item.issue_url), " → " + item.task_id + " (Triage)"); }),
        result.existing.map(function (item) { return h("p", {key: item.task_id}, "Already linked: " + item.issue_url + " → " + item.task_id + " (" + item.status + ")"); }),
        result.skipped.map(function (item) { return h("p", {key: item.issue_url}, item.issue_url + ": " + item.reason); }),
        h("small", null, "Batch report: " + result.batch_id + ". Existing cards preserved. No execution approval granted.")) : null);
  }
  function ResultPanel() {
    var a=R.useState([]), rows=a[0], setRows=a[1];
    var b=R.useState(""), message=b[0], setMessage=b[1];
    var c=R.useState(false), busy=c[0], setBusy=c[1];
    async function refresh() { try { setRows((await api("/github-results")).results); } catch(e) { setMessage(e.message); } }
    R.useEffect(function(){ refresh(); }, []);
    async function send(row) {
      setBusy(true); setMessage("");
      try {
        var result=await api("/github-return", {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({task_id:row.task_id,snapshot_sha256:row.snapshot_sha256})});
        setMessage(result.issue_url+" → "+result.status+". Human acceptance is still required.");
      } catch(e) { setMessage(e.message); } finally { setBusy(false); }
    }
    return h("section",{style:{border:"1px solid #A9B7A4",padding:"16px",marginBottom:"16px"}},
      h("strong",null,"Hermes → GitHub review"),
      h("p",null,"Return worker summaries and artifact evidence to GitHub. This does not accept or close an issue."),
      h("button",{onClick:refresh,disabled:busy},"Refresh results"),
      rows.map(function(row){ return h("div",{key:row.task_id},h("p",null,row.title+" · "+row.status),
        h("details",null,h("summary",null,"Inspect return evidence"),h("pre",{style:{whiteSpace:"pre-wrap"}},JSON.stringify(row,null,2))),
        h("button",{disabled:busy,onClick:function(){send(row);}},"Send results to GitHub "+row.proposed_status)); }),
      message?h("p",{role:"status"},message):null);
  }
  function Panel() {
    var choicesState = R.useState([]), choices = choicesState[0], setChoices = choicesState[1];
    var taskState = R.useState("issue6-roster"), selected = taskState[0], setSelected = taskState[1];
    var a = R.useState(null), data = a[0], setData = a[1];
    var b = R.useState(""), error = b[0], setError = b[1];
    var c = R.useState(""), phrase = c[0], setPhrase = c[1];
    var d = R.useState(false), busy = d[0], setBusy = d[1];
    var e = R.useState(""), doc = e[0], setDoc = e[1];
    var f = R.useState(window.location.href), location = f[0], setLocation = f[1];
    var url = new URL(location), visible = url.searchParams.get("profile") === "jeeves";
    var onPage = url.pathname === "/jeeves-launch";
    R.useEffect(function () {
      var alive = true;
      function refresh() {
        if (!alive) return;
        setLocation(window.location.href);
        var u = new URL(window.location.href);
        if (u.searchParams.get("profile") !== "jeeves" || u.pathname !== "/jeeves-launch") return;
        api("/status", undefined, selected).then(function (s) { if (alive) { setData(s); setError(""); } })
          .catch(function (err) { if (alive) setError(String(err.message || err)); });
      }
      api("/tasks").then(function (catalog) { if (alive) setChoices(catalog.tasks); }).catch(function (err) { if (alive) setError(String(err.message || err)); });
      refresh();
      var timer = window.setInterval(refresh, 3000);
      return function () { alive = false; window.clearInterval(timer); };
    }, [selected]);
    function changeTask(event) { setSelected(event.target.value); setData(null); setPhrase(""); setDoc(""); setError(""); }
    async function launch() {
      if (busy || !data || !data.can_launch || phrase !== data.approval_phrase) return;
      setBusy(true); setError("");
      try {
        await api("/start", {method: "POST", headers: {"Content-Type": "application/json"},
          body: JSON.stringify({phrase: phrase, card_sha256: data.card_sha256, contract_sha256: data.contract_sha256})}, selected);
        setPhrase(""); setData(await api("/status", undefined, selected));
      } catch (err) { setError(String(err.message || err)); }
      finally { setBusy(false); }
    }
    async function readDocument() {
      try { setDoc((await api("/document", undefined, selected)).markdown); }
      catch (err) { setError(String(err.message || err)); }
    }
    function download() {
      var link = document.createElement("a"), blob = new Blob([doc], {type: "text/markdown;charset=utf-8"});
      var object = URL.createObjectURL(blob);
      link.href = object; link.download = data.filename; link.click();
      window.setTimeout(function () { URL.revokeObjectURL(object); }, 1000);
    }
    if (!visible || !onPage) return null;
    var style = {border: "1px solid #A9B7A4", borderRadius: "8px", padding: "16px", marginBottom: "16px"};
    var button = {padding: "8px 14px", marginRight: "8px", border: "1px solid #A9B7A4", borderRadius: "5px", cursor: "pointer"};
    return h("section", {style: style},
      h(IntakePanel, null),
      h(ResultPanel, null),
      h("strong", null, "Jeeves · Approved document tasks"),
      h("p", null, h("label", null, "Task ", h("select", {value: selected, onChange: changeTask, disabled: busy},
        choices.map(function (task) { return h("option", {key: task.selector, value: task.selector}, "Issue #" + task.issue_number + ": " + task.title); })))),
      h("p", null, data && data.card_status === "done" ? "This document task is complete. Its document remains available below." : "Approve one document draft using the existing local Jeeves model. No tools or children. The result goes to Review."),
      h("p", null, data ? (data.card_status === "done" ? "Completed" : "Card: " + data.card_status + " · Run: " + data.launch_state) : "Checking the existing card…"),
      error ? h("p", {role: "alert", style: {color: "#b84646"}}, error) : null,
      data ? h("details", null, h("summary", null, "Review exact task scope"), h("pre", {style: {whiteSpace: "pre-wrap"}}, data.scope)) : null,
      data && data.can_launch ? h("div", null,
        h("label", null, "Type " + data.approval_phrase + " ", h("input", {value: phrase, onChange: function (event) {setPhrase(event.target.value);},
          autoComplete: "off", style: {padding: "8px", border: "1px solid #A9B7A4", marginRight: "8px"}})),
        h("button", {style: button, disabled: busy || !data || phrase !== data.approval_phrase, onClick: launch}, busy ? "Starting…" : "Approve and run")) : null,
      data && ["launching", "running"].includes(data.launch_state) ? h("p", null, (data.launch_state === "launching" ? "Launch requested; waiting for the worker." : "Guarded worker is running.") + " This panel refreshes automatically. Do not launch the card with the ordinary dispatcher.") : null,
      data && (data.launch_state === "incomplete" || data.evidence_status === "INCOMPLETE") ?
        h("p", {role: "alert"}, "Run stopped for review. No automatic retry. Error: " + (data.error_type || "See dashboard-worker.log in the workspace.")) : null,
      data && data.document_available ? h("button", {style: button, onClick: readDocument}, "Read document") : null,
      doc ? h("div", null, h("button", {style: button, onClick: download}, "Download document"),
        h("pre", {style: {whiteSpace: "pre-wrap", maxHeight: "450px", overflow: "auto", marginTop: "12px"}}, doc)) : null,
      data ? h("small", null, "Workspace: " + data.workspace) : null);
  }
  registry.register("landmarksignal-launch", Panel);
})();
