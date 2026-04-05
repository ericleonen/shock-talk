export default function Header() {
  return (
    <header className="flex-none w-full border-b border-gray-200 bg-white px-6 h-14 flex items-center justify-between">
      <div className="flex items-center gap-2">
        <span className="text-lg font-semibold tracking-tight text-gray-900">
          Shock<span className="text-green-600">Talk</span>
        </span>
        <span className="text-xs font-medium text-gray-400 border border-gray-200 rounded px-1.5 py-0.5 ml-1">
          beta
        </span>
      </div>
      <nav className="flex items-center gap-6">
        <a
          href="#"
          className="text-sm text-gray-500 hover:text-gray-900 transition-colors"
        >
          Docs
        </a>
        <a
          href="#"
          className="text-sm text-gray-500 hover:text-gray-900 transition-colors"
        >
          Examples
        </a>
        <a
          href="https://github.com/ericleonen/dsge-visualizer"
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm text-gray-500 hover:text-gray-900 transition-colors"
        >
          GitHub
        </a>
      </nav>
    </header>
  );
}
