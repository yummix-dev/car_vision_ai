// The only module that knows `window.Telegram` exists.
//
// Outside Telegram — a plain browser, which is how this app is developed and
// demoed — every call is a no-op and `user` is null. Callers never branch on
// the environment; they just call and get nothing back.

const wa = window.Telegram?.WebApp || null;

/** Telegram sends `id`, `first_name`, `username`… — snake_case, as in initData. */
function readUser() {
  const u = wa?.initDataUnsafe?.user;
  if (!u?.id) return null;
  return {
    id: u.id,
    firstName: u.first_name || "",
    lastName: u.last_name || "",
    username: u.username || "",
    fullName: [u.first_name, u.last_name].filter(Boolean).join(" "),
  };
}

export const tg = {
  available: Boolean(wa),

  // initDataUnsafe is only for display. This raw string is what the backend
  // verifies — never trust the parsed object for anything that matters.
  initData: wa?.initData || "",

  user: readUser(),

  // The `startapp` payload the mini-app was opened with — how a referral
  // arrives. Only meaningful inside Telegram.
  startParam: wa?.initDataUnsafe?.start_param || "",

  // Every call is `?.()` rather than `?.` on `wa` alone: parts of this API
  // arrived in later Bot API versions (BackButton and openTelegramLink in 6.1),
  // and an old Telegram client exposes WebApp without them.
  ready() {
    wa?.ready?.();
    wa?.expand?.();
  },

  /** Wire the native header back button. Returns a setter for its visibility. */
  onBack(handler) {
    if (!wa?.BackButton?.onClick) return () => {};
    wa.BackButton.onClick(handler);
    return (visible) => (visible ? wa.BackButton.show() : wa.BackButton.hide());
  },

  // Feature-detected, not version-checked: requestWriteAccess landed in Bot API
  // 6.9 and downloadFile in 8.0, so a current client has them and an older one
  // simply does not. Callers hide the affordance rather than offering a button
  // that cannot work.
  canShare: Boolean(wa?.requestWriteAccess),
  canDownload: Boolean(wa?.downloadFile),

  /** Native permission prompt for the bot to message the user. */
  requestWriteAccess() {
    return new Promise((resolve) => {
      if (!wa?.requestWriteAccess) return resolve(false);
      try {
        wa.requestWriteAccess((granted) => resolve(Boolean(granted)));
      } catch {
        resolve(false);
      }
    });
  },

  /** Native "save file" prompt. Resolves false when unavailable or declined. */
  downloadFile(params) {
    return new Promise((resolve) => {
      if (!wa?.downloadFile) return resolve(false);
      try {
        wa.downloadFile(params, (accepted) => resolve(Boolean(accepted)));
      } catch {
        resolve(false);
      }
    });
  },

  close() {
    wa?.close?.();
  },

  /** Vertical swipe closes the mini-app by default, which collides with a
   *  scrolling screen and with dragging the before/after handle. 7.7+. */
  disableVerticalSwipes() {
    wa?.disableVerticalSwipes?.();
  },

  /** Push OUR palette out to the client chrome. This is the opposite of
   *  adopting themeParams — the app keeps its own fixed dark design, and this
   *  only stops the seam between client and app from looking like two apps. */
  setColors(color) {
    wa?.setHeaderColor?.(color);
    wa?.setBackgroundColor?.(color);
  },

  // Native QR scanner — no camera library, no CSP exception. 6.4+.
  canScanQr: Boolean(wa?.showScanQrPopup),

  /** Open the scanner; resolves with the scanned text, or null if cancelled. */
  scanQr(text) {
    return new Promise((resolve) => {
      if (!wa?.showScanQrPopup) return resolve(null);
      let done = false;
      try {
        wa.showScanQrPopup({ text: text || "" }, (result) => {
          done = true;
          wa.closeScanQrPopup?.();
          resolve(result || null);
          return true; // close the popup
        });
        // If the user dismisses without scanning, Telegram fires no callback;
        // resolve null once the popup is closed by the platform.
        wa.onEvent?.("scanQrPopupClosed", () => { if (!done) resolve(null); });
      } catch {
        resolve(null);
      }
    });
  },

  openTelegramLink(url) {
    if (wa?.openTelegramLink) {
      wa.openTelegramLink(url);
      return;
    }
    // In a browser the deep link still works as an ordinary https://t.me URL.
    window.open(url, "_blank", "noopener");
  },
};
