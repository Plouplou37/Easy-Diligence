/** The sign-in and password screens: one card, centred on the plain background. */
export const AuthShell = ({ title, subtitle, children }) => (
  <div className="bg-auth min-h-screen overflow-y-auto flex items-center justify-center px-4 py-10 sm:px-6">
    <div className="w-full max-w-md">
      <p className="mb-6 text-center text-lg font-bold tracking-tight text-content">
        Easy Diligence
      </p>
      <div className="bg-surface border border-border rounded-2xl p-8 shadow-lg">
        <h1 className="text-2xl font-bold tracking-tight text-content">{title}</h1>
        <p className="mt-1.5 mb-6 text-sm text-content-secondary">{subtitle}</p>
        {children}
      </div>
    </div>
  </div>
);
