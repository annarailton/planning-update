/**
 * Jobs feature - background job management with real-time updates.
 *
 * @example
 * ```tsx
 * import { useCreateJob, useJobStream } from '@/features/jobs';
 *
 * function FileProcessor({ fileId }: { fileId: string }) {
 *   const { createJob, isLoading: isCreating } = useCreateJob();
 *   const [jobId, setJobId] = useState<string | null>(null);
 *   const { status, progress, result } = useJobStream(jobId);
 *
 *   const handleProcess = async () => {
 *     const { jobId } = await createJob({
 *       jobType: 'process_file',
 *       payload: { fileId },
 *     });
 *     setJobId(jobId);
 *   };
 *
 *   return (
 *     <div>
 *       <button onClick={handleProcess} disabled={isCreating}>
 *         Process
 *       </button>
 *       {jobId && (
 *         <div>
 *           <ProgressBar value={progress} />
 *           <span>{status}</span>
 *         </div>
 *       )}
 *     </div>
 *   );
 * }
 * ```
 */

// Components
export { JobsDemo } from "./components/JobsDemo";

// Hooks
export { useCreateJob, useJobStream } from "./hooks";

// Types
export type {
  Job,
  JobStatus,
  CreateJobRequest,
  CreateJobResponse,
  JobStreamEvent,
  UseJobStreamResult,
} from "./types/job.types";

// Services
export { jobService } from "./services/jobService";
