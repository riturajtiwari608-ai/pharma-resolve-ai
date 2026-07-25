import ComplaintForm from "../components/ComplaintForm";
import CopilotPanel from "../components/CopilotPanel";

export default function ComplaintWorkspace() {
  return (
    <main className="application-shell">
      <ComplaintForm />
      <CopilotPanel />
    </main>
  );
}