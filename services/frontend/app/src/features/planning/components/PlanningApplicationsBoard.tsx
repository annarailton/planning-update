import { ExternalLink, MapPinned, FileText, Landmark } from "lucide-react";
import { usePlanningApplications } from "../hooks/usePlanningApplications";
import type { PlanningApplicationSummary } from "../types/planning.types";
import { ErrorMessage } from "../../../shared/components/ErrorMessage";

function PlanningApplicationCard({
  application,
}: {
  application: PlanningApplicationSummary;
}) {
  return (
    <article className="rounded-3xl border border-emerald-100 bg-white p-6 shadow-sm shadow-emerald-950/5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-emerald-700">
            {application.applicationId}
          </p>
          <h3 className="mt-2 text-lg font-semibold text-slate-900">
            {application.location}
          </h3>
        </div>
        <a
          href={application.detailUrl}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-2 rounded-full border border-emerald-200 px-3 py-2 text-sm font-medium text-emerald-800 transition-colors hover:border-emerald-400 hover:bg-emerald-50"
        >
          Open
          <ExternalLink className="h-4 w-4" />
        </a>
      </div>

      <dl className="mt-5 grid gap-4 text-sm text-slate-700 sm:grid-cols-2">
        <div className="rounded-2xl bg-slate-50 px-4 py-3">
          <dt className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
            <Landmark className="h-4 w-4" />
            Ward
          </dt>
          <dd className="mt-2 text-base font-medium text-slate-900">
            {application.ward ?? "Not provided by source"}
          </dd>
        </div>
        <div className="rounded-2xl bg-slate-50 px-4 py-3">
          <dt className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
            <MapPinned className="h-4 w-4" />
            Location
          </dt>
          <dd className="mt-2 text-base font-medium text-slate-900">
            {application.location}
          </dd>
        </div>
      </dl>

      <div className="mt-5 rounded-2xl bg-emerald-50/70 px-4 py-4">
        <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-emerald-800">
          <FileText className="h-4 w-4" />
          Summary
        </p>
        <p className="mt-2 text-sm leading-7 text-slate-700">
          {application.summary}
        </p>
      </div>
    </article>
  );
}

export function PlanningApplicationsBoard() {
  const { data, isLoading, error } = usePlanningApplications();

  if (isLoading) {
    return (
      <div className="rounded-[2rem] border border-dashed border-emerald-200 bg-white/80 p-8 text-sm text-slate-600">
        Loading the latest Oxford planning applications for Hinksey Park...
      </div>
    );
  }

  if (error) {
    return <ErrorMessage title="Planning data unavailable" message={error} />;
  }

  if (!data) {
    return (
      <ErrorMessage
        title="Planning data unavailable"
        message="No planning data was returned."
      />
    );
  }

  return (
    <section className="space-y-6">
      <div className="rounded-[2rem] border border-emerald-100 bg-gradient-to-br from-emerald-50 via-white to-amber-50 p-8">
        <p className="text-xs font-semibold uppercase tracking-[0.28em] text-emerald-700">
          Oxford Weekly List
        </p>
        <div className="mt-3 flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 className="text-3xl font-semibold tracking-tight text-slate-950">
              {data.filters.ward ?? "All wards"}
            </h2>
            <p className="mt-2 max-w-2xl text-sm leading-7 text-slate-600">
              Showing {data.totalCount} application
              {data.totalCount === 1 ? "" : "s"} from the week beginning{" "}
              {data.filters.weekBeginning}. This first version is focused on the
              most recent Hinksey Park list, with the backend already shaped for
              broader filters next.
            </p>
          </div>
          <div className="rounded-2xl bg-slate-950 px-5 py-4 text-white shadow-lg shadow-slate-950/10">
            <p className="text-xs uppercase tracking-[0.24em] text-emerald-200">
              Source Mode
            </p>
            <p className="mt-2 text-lg font-semibold capitalize">
              {data.filters.dateType}
            </p>
          </div>
        </div>
      </div>

      {data.applications.length === 0 ? (
        <div className="rounded-[2rem] border border-amber-200 bg-amber-50 p-8 text-sm text-amber-950">
          No planning applications matched this weekly list.
        </div>
      ) : (
        <div className="grid gap-5">
          {data.applications.map((application) => (
            <PlanningApplicationCard
              key={application.applicationId}
              application={application}
            />
          ))}
        </div>
      )}
    </section>
  );
}
