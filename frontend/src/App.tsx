import { useEffect, useRef } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { BottomNav } from "./components/BottomNav";
import { isOnboardingDone } from "./lib/storage";
import { extractVideoUrlFromText } from "./lib/videoUrl";

export default function App() {
  const location = useLocation();
  const navigate = useNavigate();
  const redirectedRef = useRef(false);

  useEffect(() => {
    if (!isOnboardingDone() && !location.pathname.startsWith("/onboarding")) {
      navigate("/onboarding", { replace: true });
    }
  }, [location.pathname, navigate]);

  useEffect(() => {
    if (redirectedRef.current) return;
    const params = new URLSearchParams(location.search);
    const shared = params.get("url") || params.get("text") || "";
    const videoUrl = extractVideoUrlFromText(shared);
    if (videoUrl && (location.pathname === "/" || location.pathname === "/home")) {
      redirectedRef.current = true;
      navigate(`/import?url=${encodeURIComponent(videoUrl)}`, { replace: true });
    }
  }, [location, navigate]);

  const fullBleed = location.pathname.startsWith("/onboarding");
  const hideNav = location.pathname.startsWith("/onboarding");

  return (
    <>
      <div className={fullBleed ? "app-shell app-shell--full" : "app-shell"}>
        <Outlet />
      </div>
      {!hideNav ? <BottomNav /> : null}
    </>
  );
}
