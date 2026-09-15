"use client";

export default function Error({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return <main className="mx-auto flex max-w-xl flex-col items-center justify-center px-6 py-32 text-center"><span className="eyebrow text-danger">Application error</span><h1 className="mt-3 text-3xl font-bold">The workspace hit an unexpected state.</h1><p className="mt-3 text-sm text-quiet">No analysis was discarded. Try the view again.</p><button className="button-primary mt-7" onClick={() => reset()}>Retry view</button></main>;
}
