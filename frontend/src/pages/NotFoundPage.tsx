import { Link } from "react-router-dom";

import { PageHeader } from "../components/ui";

export function NotFoundPage() {
  return (
    <>
      <PageHeader title="Page not found" description="That address doesn't match any screen." />
      <Link to="/">Back to the dashboard</Link>
    </>
  );
}

export function ForbiddenPage() {
  return (
    <>
      <PageHeader
        title="Not available for your role"
        description="Your account doesn't have access to this screen. Ask the administrator if you need it."
      />
      <Link to="/">Back to the dashboard</Link>
    </>
  );
}
