import { motion } from "motion/react";
import {
  RealtimeChatInterface,
  RealtimePageHeader,
} from "../features/realtime";

export function RealtimeAgentPage() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.3 }}
      className="max-w-5xl mx-auto p-6"
    >
      <RealtimePageHeader />
      <RealtimeChatInterface />
    </motion.div>
  );
}
