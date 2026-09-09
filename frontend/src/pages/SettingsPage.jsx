export default function SettingsPage() {
  return (
    <div>
      <h1 className="page-title">Settings & privacy</h1>
      <p className="page-sub">Consent, privacy, and system configuration notes.</p>

      <div className="panel card">
        <h2>Privacy notice</h2>
        <ul className="disclaimer">
          <li>Webcam video is processed for live inference and is not continuously stored.</li>
          <li>When you save an observation, only derived results are kept (expression, confidence, timestamps, session ID).</li>
          <li>Access requires authenticated caregiver login with role-based authorization.</li>
          <li>Secrets and keys must live in environment variables — never hard-code them.</li>
        </ul>
      </div>

      <div className="panel card">
        <h2>Consent reminder</h2>
        <p className="disclaimer">
          Obtain informed consent before monitoring. Inform participants that predictions describe observable facial
          expressions only and are not medical diagnoses or true emotional-state determinations.
        </p>
      </div>

      <div className="panel card">
        <h2>System labels</h2>
        <p className="disclaimer">
          Preferred wording: observable facial expression · AI prediction · confidence score · caregiver attention
          indicator.
        </p>
      </div>
    </div>
  );
}
