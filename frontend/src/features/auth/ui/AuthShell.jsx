/** The sign-in and sign-up screens: a card on the left, the logo on the right. */
export const AuthShell = ({ title, subtitle, children }) => (
  <div className="bg-auth min-h-screen overflow-y-auto flex items-center justify-center px-4 py-6 sm:px-6 lg:px-8">
    <div className="flex flex-row w-full max-w-6xl rounded-3xl p-4 sm:p-6 gap-8 shadow-lg bg-bleu/85">
      <div className="w-full lg:w-[42%] xl:w-[38%] flex justify-center">
        <div className="w-full max-w-md bg-surface shadow-xl rounded-3xl p-8 border border-border">
          <h1 className="text-center text-3xl font-bold text-content">{title}</h1>
          <p className="mt-2 mb-8 text-center text-sm text-content-secondary">{subtitle}</p>
          {children}
        </div>
      </div>
      <div className="hidden lg:flex flex-1 items-center justify-center">
        <img src="/logo-white.svg" alt="Easy Diligence" className="w-[80%] h-auto" />
      </div>
    </div>
  </div>
);
