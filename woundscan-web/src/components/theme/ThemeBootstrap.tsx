/**
 * Inline pre-paint script that sets the initial theme class on <html>
 * before React hydration, so users never see a light/dark flash.
 *
 * Order of preference: explicit user setting in localStorage → OS scheme.
 */
export function ThemeBootstrap() {
  const code = `(()=>{try{
    var s=localStorage.getItem('ws-theme');
    var d=s?s==='dark':window.matchMedia('(prefers-color-scheme: dark)').matches;
    document.documentElement.classList.toggle('dark',d);
  }catch(_){}})();`;
  return <script dangerouslySetInnerHTML={{ __html: code }} />;
}
