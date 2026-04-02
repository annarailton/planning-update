import { motion } from "motion/react";
import { TemporalDemo } from "../features/temporal";

export default function TemporalJobPage() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.3 }}
      className="max-w-4xl mx-auto p-6"
    >
      <TemporalDemo />
    </motion.div>
  );
}
