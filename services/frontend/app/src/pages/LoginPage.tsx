import { SignIn } from "@clerk/clerk-react";
import { ConnectivityScene } from "../shared/components/landing/ConnectivityScene";
import { motion } from "motion/react";
import { Sparkles, ArrowLeft } from "lucide-react";
import { Link } from "react-router-dom";

export function LoginPage() {
  return (
    <div className="relative min-h-screen bg-gray-50 dark:bg-slate-950 flex items-center justify-center overflow-hidden transition-colors duration-300">
      {/* 3D Background */}
      <div className="absolute inset-0 opacity-50">
        <ConnectivityScene />
      </div>

      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5 }}
        className="relative z-10 w-full max-w-md px-4"
      >
        <Link
          to="/"
          className="inline-flex items-center gap-2 text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white mb-8 transition-colors text-sm font-medium"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Home
        </Link>

        {/* Brand Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 shadow-lg shadow-indigo-500/20 mb-4">
            <Sparkles className="w-6 h-6 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
            Welcome Back
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Sign in to access your dashboard
          </p>
        </div>

        {/* Login Card */}
        <div className="bg-white/80 dark:bg-white/5 backdrop-blur-xl border border-gray-200 dark:border-white/10 rounded-2xl p-2 shadow-2xl">
          <SignIn
            appearance={{
              elements: {
                rootBox: "w-full",
                card: "bg-transparent shadow-none w-full p-6",
                headerTitle: "hidden",
                headerSubtitle: "hidden",
                socialButtonsBlockButton:
                  "bg-white/10 border-white/10 text-white hover:bg-white/20",
                socialButtonsBlockButtonText: "text-white",
                dividerLine: "bg-white/10",
                dividerText: "text-gray-400",
                formFieldLabel: "text-gray-300",
                formFieldInput:
                  "bg-white/5 border-white/10 text-white focus:border-indigo-500",
                footerActionText: "text-gray-400",
                footerActionLink: "text-indigo-400 hover:text-indigo-300",
                formButtonPrimary:
                  "bg-indigo-600 hover:bg-indigo-500 text-white",
                formFieldAction: "text-indigo-400 hover:text-indigo-300",
                identityPreviewText: "text-white",
                identityPreviewEditButton:
                  "text-indigo-400 hover:text-indigo-300",
              },
              layout: {
                socialButtonsPlacement: "bottom",
                showOptionalFields: false,
              },
            }}
          />
        </div>

        <p className="text-center mt-8 text-gray-500 text-sm">
          Powered by Tomoro Fullstack Kit
        </p>
      </motion.div>
    </div>
  );
}
