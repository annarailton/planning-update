import { motion } from "motion/react";
import { JobsDemo } from "../features/jobs";

export function JobsPage() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.3 }}
      className="max-w-4xl mx-auto p-6"
    >
      <JobsDemo />
    </motion.div>
  );
}
