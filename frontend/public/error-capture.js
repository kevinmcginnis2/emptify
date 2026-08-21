// public/error-capture.js
(function () {
  if (typeof window === "undefined") return;

  // Capture normal runtime JS errors
  window.addEventListener("error", (e) => {
    window.parent.postMessage(
      {
        type: "sandbox:error",
        errorType: "window-error",
        message: e.error?.message || e.message,
        stack: e.error?.stack || null,
        filename: e.filename,
        lineno: e.lineno,
        colno: e.colno,
      },
      "*"
    );
  });

  // Capture unhandled promise rejections
  window.addEventListener("unhandledrejection", (e) => {
    window.parent.postMessage(
      {
        type: "sandbox:error",
        errorType: "unhandled-rejection",
        message: e.reason?.message || e.reason,
        stack: e.reason?.stack || null,
      },
      "*"
    );
  });

  // Capture Next.js + Turbopack overlay errors
  // (Overlay writes to console.error)
  const origError = console.error;
  console.error = (...args) => {
    try {
      window.parent.postMessage(
        {
          type: "sandbox:error",
          errorType: "console-error",
          message: args.map((a) => (a?.message ? a.message : a)).join("\n"),
          stack: args.find((a) => a?.stack)?.stack || null,
        },
        "*"
      );
    } catch (err) {}
    origError(...args);
  };
})();
