import Link from 'next/link';

export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <h1 className="text-5xl font-bold mb-8">EventRelay</h1>
      <p className="text-xl text-gray-600 mb-12 text-center max-w-2xl">
        Production-ready AI Infrastructure Platform Generator.
        Transform YouTube URLs into deployable AI applications.
      </p>
      
      <div className="flex gap-4">
        <Link 
          href="/dashboard" 
          className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
        >
          Dashboard
        </Link>
        <Link 
          href="/api" 
          className="px-6 py-3 border border-gray-300 rounded-lg hover:bg-gray-50 transition"
        >
          API Docs
        </Link>
      </div>
    </main>
  );
}