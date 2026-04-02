import { motion } from "motion/react";
import { PlanningApplicationsBoard } from "../features/planning";

export function PlanningApplicationsPage() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -18 }}
      transition={{ duration: 0.3 }}
      className="mx-auto min-h-screen max-w-5xl px-6 py-10"
    >
      <div className="mb-8">
        <p className="text-sm font-semibold uppercase tracking-[0.3em] text-emerald-700">
          Planning Watch
        </p>
        <h1 className="mt-3 text-4xl font-semibold tracking-tight text-slate-950">
          Oxford planning applications
        </h1>
        <p className="mt-3 max-w-3xl text-sm leading-7 text-slate-600">
          A simple weekly planning view for Oxford City Council, starting with
          the latest Hinksey Park ward applications and direct links back to
          each source record.
        </p>
      </div>

      <PlanningApplicationsBoard />
    </motion.div>
  );
}
