const indexHtml = new TextDecoder().decode(Uint8Array.from(atob("PCFET0NUWVBFIGh0bWw+PGh0bWwgbGFuZz0iZGUiPjxoZWFkPjxtZXRhIGNoYXJzZXQ9IlVURi04Ij48bWV0YSBuYW1lPSJ2aWV3cG9ydCIgY29udGVudD0id2lkdGg9ZGV2aWNlLXdpZHRoLCBpbml0aWFsLXNjYWxlPTEiPjx0aXRsZT5IZXksIFN0dXRlbnNlZSEg4oCTIFZlcmFuc3RhbHR1bmdlbiB1bmQgVGVybWluZTwvdGl0bGU+PCEtLVNTUl9PR19UQUdTLS0+PCEtLVNTUl9KU09OX0xELS0+PCEtLVNTUl9CUkVBRENSVU1CLS0+PG1ldGEgbmFtZT0iZGVzY3JpcHRpb24iIGNvbnRlbnQ9IkFsbGUgVmVyYW5zdGFsdHVuZ2VuIGluIFN0dXRlbnNlZSBhdWYgZWluZW4gQmxpY2s6IEZlc3RlLCBNw6Rya3RlLCBTcG9ydCwgS2lyY2hlLCBLaW5kZXJhbmdlYm90ZSB1bmQgbWVoci4gR2VmaWx0ZXJ0IG5hY2ggT3J0c3RlaWwgdW5kIEthdGVnb3JpZS4iPjxsaW5rIHJlbD0iaWNvbiIgdHlwZT0iaW1hZ2UvcG5nIiBocmVmPSIvZmF2aWNvbi5wbmciPjxzdHlsZT5TVFlMRV9DU1NfUExBQ0VIT0xERVI8L3N0eWxlPjwvaGVhZD48Ym9keT48ZGl2IGNsYXNzPSJwYWdlLWxlZnQiPjxoZWFkZXI+PGRpdiBjbGFzcz0iaGVhZGVyLWlubmVyIj48c3ZnIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyIgdmlld0JveD0iMCAwIDU1MCAxMDAiIGNsYXNzPSJzY2hkdWRlc2VlLWxvZ28iIHN0eWxlPSJoZWlnaHQ6NjhweDt3aWR0aDphdXRvOyI+PGRlZnM+PGNsaXBQYXRoIGlkPSJzLWNsaXAiPjx0ZXh0IHg9IjU0IiB5PSI3OCIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1mYW1pbHk9InN5c3RlbS11aSwtYXBwbGUtc3lzdGVtLHNhbnMtc2VyaWYiIGZvbnQtd2VpZ2h0PSI4MDAiIGZvbnQtc2l6ZT0iODAiPlM8L3RleHQ+PC9jbGlwUGF0aD48Y2xpcFBhdGggaWQ9InRpcC1jbGlwIj48cmVjdCB4PSI1MiIgeT0iOCIgd2lkdGg9IjI0IiBoZWlnaHQ9IjMyIi8+PC9jbGlwUGF0aD48L2RlZnM+PHRleHQgeD0iNTQiIHk9Ijc4IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmb250LWZhbWlseT0ic3lzdGVtLXVpLC1hcHBsZS1zeXN0ZW0sc2Fucy1zZXJpZiIgZm9udC13ZWlnaHQ9IjgwMCIgZm9udC1zaXplPSI4MCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjZmZmZmZmIiBzdHJva2Utd2lkdGg9IjQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiPlM8L3RleHQ+PHRleHQgeD0iNTQiIHk9Ijc4IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmb250LWZhbWlseT0ic3lzdGVtLXVpLC1hcHBsZS1zeXN0ZW0sc2Fucy1zZXJpZiIgZm9udC13ZWlnaHQ9IjgwMCIgZm9udC1zaXplPSI4MCIgZmlsbD0iI2ZhYjgwMCI+UzwvdGV4dD48dGV4dCB4PSI1NCIgeT0iNzgiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtZmFtaWx5PSJzeXN0ZW0tdWksLWFwcGxlLXN5c3RlbSxzYW5zLXNlcmlmIiBmb250LXdlaWdodD0iODAwIiBmb250LXNpemU9IjgwIiBmaWxsPSIjZGQyOTFhIiBjbGlwLXBhdGg9InVybCgjdGlwLWNsaXApIj5TPC90ZXh0PjxnIGNsaXAtcGF0aD0idXJsKCNzLWNsaXApIj48cGF0aCBjbGFzcz0id2F2ZS1pbm5lciIgZD0iTS01IDYwIFE1IDU0IDE1IDYwIFEyNSA2NiAzNSA2MCBRNDUgNTQgNTUgNjAgUTY1IDY2IDc1IDYwIFE4NSA1NCA5NSA2MCIgc3Ryb2tlPSIjMGQzYTcxIiBzdHJva2Utd2lkdGg9IjEwIiBmaWxsPSJub25lIiBzdHJva2UtbGluZWNhcD0icm91bmQiIG9wYWNpdHk9IjEiLz48cGF0aCBjbGFzcz0id2F2ZS1pbm5lciIgZD0iTS01IDY5IFE1IDYzIDE1IDY5IFEyNSA3NSAzNSA2OSBRNDUgNjMgNTUgNjkgUTY1IDc1IDc1IDY5IFE4NSA2MyA5NSA2OSIgc3Ryb2tlPSIjMWE1Mjk5IiBzdHJva2Utd2lkdGg9IjEwIiBmaWxsPSJub25lIiBzdHJva2UtbGluZWNhcD0icm91bmQiIG9wYWNpdHk9IjEiIHN0eWxlPSJhbmltYXRpb24tZGVsYXk6LTFzIi8+PHBhdGggY2xhc3M9IndhdmUtaW5uZXIiIGQ9Ik0tNSA3OCBRNSA3MiAxNSA3OCBRMjUgODQgMzUgNzggUTQ1IDcyIDU1IDc4IFE2NSA4NCA3NSA3OCBRODUgNzIgOTUgNzgiIHN0cm9rZT0iIzNhN2JjOCIgc3Ryb2tlLXdpZHRoPSIxMCIgZmlsbD0ibm9uZSIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBvcGFjaXR5PSIxIiBzdHlsZT0iYW5pbWF0aW9uLWRlbGF5Oi0ycyIvPjwvZz48dGV4dCB4PSIxNDAiIHk9IjYwIiBmb250LWZhbWlseT0ic3lzdGVtLXVpLC1hcHBsZS1zeXN0ZW0sc2Fucy1zZXJpZiIgZm9udC13ZWlnaHQ9IjcwMCIgZm9udC1zaXplPSIyNiIgZmlsbD0iI2ZmZmZmZiI+SGV5LCBTdHV0ZW5zZWUhPC90ZXh0Pjwvc3ZnPjwvZGl2PjwvaGVhZGVyPjxkaXYgY2xhc3M9ImNvbnRyb2xzLXdyYXAiPjxkaXYgY2xhc3M9ImNvbnRyb2xzIj48ZGl2IGNsYXNzPSJjb250cm9scy1yb3ciPjxpbnB1dCB0eXBlPSJ0ZXh0IiBpZD0ic2VhcmNoIiBwbGFjZWhvbGRlcj0iU3VjaGVu4oCmIiBhcmlhLWxhYmVsPSJTdWNoZSIgb25pbnB1dD0iZGVib3VuY2VTZWFyY2goKSI+PGlucHV0IHR5cGU9ImRhdGUiIGlkPSJkYXRlLWZyb20iIG9uY2hhbmdlPSJsb2FkRXZlbnRzKDEpIiB0aXRsZT0iVm9uIj48L2Rpdj48ZGl2IGNsYXNzPSJjb250cm9scy1yb3ciPjxkaXYgY2xhc3M9ImZpbHRlci1wb3BvdmVyIiBpZD0idGhlbWUtcG9wb3ZlciI+PGJ1dHRvbiBjbGFzcz0iZmlsdGVyLWJ0biIgb25jbGljaz0idG9nZ2xlRmlsdGVyUG9wb3ZlcigndGhlbWUnKSIgaWQ9InRoZW1lLWJ0biIgYXJpYS1leHBhbmRlZD0iZmFsc2UiPkthdGVnb3JpZSDilr48L2J1dHRvbj48ZGl2IGNsYXNzPSJwb3BvdmVyLWRyb3Bkb3duIiBpZD0idGhlbWUtZHJvcGRvd24iPjwvZGl2PjwvZGl2PjxkaXYgY2xhc3M9ImZpbHRlci1wb3BvdmVyIiBpZD0ibG9jYXRpb24tcG9wb3ZlciI+PGJ1dHRvbiBjbGFzcz0iZmlsdGVyLWJ0biIgb25jbGljaz0idG9nZ2xlRmlsdGVyUG9wb3ZlcignbG9jYXRpb24nKSIgaWQ9ImxvY2F0aW9uLWJ0biIgYXJpYS1leHBhbmRlZD0iZmFsc2UiPk9ydHN0ZWlsIOKWvjwvYnV0dG9uPjxkaXYgY2xhc3M9InBvcG92ZXItZHJvcGRvd24iIGlkPSJsb2NhdGlvbi1kcm9wZG93biI+PC9kaXY+PC9kaXY+PGRpdiBjbGFzcz0iZmlsdGVyLXBvcG92ZXIiIGlkPSJvcmdhbml6ZXItcG9wb3ZlciI+PGJ1dHRvbiBjbGFzcz0iZmlsdGVyLWJ0biIgb25jbGljaz0idG9nZ2xlRmlsdGVyUG9wb3Zlcignb3JnYW5pemVyJykiIGlkPSJvcmdhbml6ZXItYnRuIiBhcmlhLWV4cGFuZGVkPSJmYWxzZSI+VmVyYW5zdGFsdGVyIOKWvjwvYnV0dG9uPjxkaXYgY2xhc3M9InBvcG92ZXItZHJvcGRvd24iIGlkPSJvcmdhbml6ZXItZHJvcGRvd24iPjxpbnB1dCB0eXBlPSJ0ZXh0IiBjbGFzcz0icG9wb3Zlci1zZWFyY2giIGlkPSJvcmdhbml6ZXItc2VhcmNoIiBwbGFjZWhvbGRlcj0iU3VjaGVu4oCmIiBvbmlucHV0PSJmaWx0ZXJPcmdhbml6ZXJzKCkiIG9uY2xpY2s9ImV2ZW50LnN0b3BQcm9wYWdhdGlvbigpIj48ZGl2IGNsYXNzPSJwb3BvdmVyLWNoaXBzIiBpZD0ib3JnYW5pemVyLWNoaXBzIj48L2Rpdj48L2Rpdj48L2Rpdj48c3BhbiBjbGFzcz0idG9nZ2xlcy1kZXNrdG9wIj48bGFiZWwgY2xhc3M9InJlY3VycmluZy10b2dnbGUtd3JhcCI+PHNwYW4gY2xhc3M9InRvZ2dsZS1zd2l0Y2giPjxpbnB1dCB0eXBlPSJjaGVja2JveCIgaWQ9ImNvbmRlbnNlZC10b2dnbGUiIG9uY2hhbmdlPSJ0b2dnbGVDb25kZW5zZWQoKSI+PHNwYW4gY2xhc3M9InRvZ2dsZS1zbGlkZXIiPjwvc3Bhbj48L3NwYW4+PHNwYW4+S29tcGFrdGFuc2ljaHQ8L3NwYW4+PC9sYWJlbD48bGFiZWwgY2xhc3M9InJlY3VycmluZy10b2dnbGUtd3JhcCI+PHNwYW4gY2xhc3M9InRvZ2dsZS1zd2l0Y2giPjxpbnB1dCB0eXBlPSJjaGVja2JveCIgaWQ9InNob3ctcmVjdXJyaW5nIiBjaGVja2VkIG9uY2hhbmdlPSJ0b2dnbGVSZWN1cnJpbmdGaWx0ZXIoKSI+PHNwYW4gY2xhc3M9InRvZ2dsZS1zbGlkZXIiPjwvc3Bhbj48L3NwYW4+PHNwYW4+WmVpZ2Ugd2llZGVyaG9sZW5kZSBUZXJtaW5lPC9zcGFuPjwvbGFiZWw+PC9zcGFuPjxzcGFuIHN0eWxlPSJwb3NpdGlvbjpyZWxhdGl2ZTtkaXNwbGF5OmlubGluZS1ibG9jayI+PGJ1dHRvbiBjbGFzcz0ic2V0dGluZ3MtYnRuIiBvbmNsaWNrPSJ0b2dnbGVTZXR0aW5nc0Ryb3Bkb3duKCkiIHRpdGxlPSJFaW5zdGVsbHVuZ2VuIj7impnvuI88L2J1dHRvbj48YnV0dG9uIGNsYXNzPSJjaGF0LWJ0biIgb25jbGljaz0idG9nZ2xlQ2hhdCgpIiB0aXRsZT0iS0ktQ2hhdCI+8J+kljwvYnV0dG9uPjxkaXYgY2xhc3M9InNldHRpbmdzLWRyb3Bkb3duIiBpZD0ic2V0dGluZ3MtZHJvcGRvd24iPjxsYWJlbCBjbGFzcz0icmVjdXJyaW5nLXRvZ2dsZS13cmFwIj48c3BhbiBjbGFzcz0idG9nZ2xlLXN3aXRjaCI+PGlucHV0IHR5cGU9ImNoZWNrYm94IiBpZD0iY29uZGVuc2VkLXRvZ2dsZS1tb2JpbGUiIG9uY2hhbmdlPSJkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgnY29uZGVuc2VkLXRvZ2dsZScpLmNoZWNrZWQ9dGhpcy5jaGVja2VkO3RvZ2dsZUNvbmRlbnNlZCgpIj48c3BhbiBjbGFzcz0idG9nZ2xlLXNsaWRlciI+PC9zcGFuPjwvc3Bhbj48c3Bhbj5Lb21wYWt0YW5zaWNodDwvc3Bhbj48L2xhYmVsPjxsYWJlbCBjbGFzcz0icmVjdXJyaW5nLXRvZ2dsZS13cmFwIj48c3BhbiBjbGFzcz0idG9nZ2xlLXN3aXRjaCI+PGlucHV0IHR5cGU9ImNoZWNrYm94IiBpZD0ic2hvdy1yZWN1cnJpbmctbW9iaWxlIiBjaGVja2VkIG9uY2hhbmdlPSJkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgnc2hvdy1yZWN1cnJpbmcnKS5jaGVja2VkPXRoaXMuY2hlY2tlZDt0b2dnbGVSZWN1cnJpbmdGaWx0ZXIoKSI+PHNwYW4gY2xhc3M9InRvZ2dsZS1zbGlkZXIiPjwvc3Bhbj48L3NwYW4+PHNwYW4+WmVpZ2Ugd2llZGVyaG9sZW5kZSBUZXJtaW5lPC9zcGFuPjwvbGFiZWw+PC9kaXY+PC9zcGFuPjxzcGFuIGNsYXNzPSJhY3RpdmUtdGFncyIgaWQ9ImFjdGl2ZS10YWdzIj48L3NwYW4+PC9kaXY+PC9kaXY+PC9kaXY+PGRpdiBjbGFzcz0iYXBwLWxheW91dCI+PG1haW4gY2xhc3M9Im1haW4tY29udGVudCI+PGRpdiBjbGFzcz0iZXZlbnRzLXdyYXAiPjwhLS1TU1JfSU5UUk8tLT48ZGl2IGlkPSJldmVudHMiIGNsYXNzPSJldmVudHMiPjwhLS1TU1JfRVZFTlRTLS0+PC9kaXY+PGRpdiBjbGFzcz0icGFnaW5hdGlvbiIgaWQ9InBhZ2luYXRpb24iPjwhLS1TU1JfUEFHSU5BVElPTi0tPjwvZGl2PjwvZGl2PjwvbWFpbj48L2Rpdj48Zm9vdGVyIHN0eWxlPSJ0ZXh0LWFsaWduOmNlbnRlcjtwYWRkaW5nOjE2cHg7Zm9udC1zaXplOjEycHg7Y29sb3I6dmFyKC0tZm9vdGVyLXRleHQpIj48YSBocmVmPSIjIiBvbmNsaWNrPSJldmVudC5wcmV2ZW50RGVmYXVsdCgpO2RvY3VtZW50LmdldEVsZW1lbnRCeUlkKCdpbXByaW50Jykuc3R5bGUuZGlzcGxheT0nYmxvY2snIiBzdHlsZT0iY29sb3I6dmFyKC0tZm9vdGVyLXRleHQpO3RleHQtZGVjb3JhdGlvbjp1bmRlcmxpbmUiPkltcHJlc3N1bTwvYT48c3BhbiBzdHlsZT0ibWFyZ2luOjAgOHB4Ij7Ctzwvc3Bhbj48c3BhbiBpZD0iZGFyay10b2dnbGUiIG9uY2xpY2s9InRvZ2dsZURhcmsoKSIgc3R5bGU9ImN1cnNvcjpwb2ludGVyO2ZvbnQtc2l6ZToxNnB4IiB0aXRsZT0iRGFyayBNb2RlIHVtc2NoYWx0ZW4iPvCfjJk8L3NwYW4+PGRpdiBpZD0iaW1wcmludCIgc3R5bGU9ImRpc3BsYXk6bm9uZTttYXJnaW4tdG9wOjEycHg7Y29sb3I6dmFyKC0taW1wcmludC10ZXh0KTtsaW5lLWhlaWdodDoxLjYiPjxzdHJvbmc+QW5nYWJlbiBnZW3DpMOfIMKnNSBUTUc8L3N0cm9uZz48YnI+IEpvaGFubmVzIFJldXRlcjxicj4gRS1NYWlsOiA8c3BhbiBpZD0iaW1wcmludC1lbWFpbCI+PC9zcGFuPjxicj48YnI+PHN0cm9uZz5IYWZ0dW5nIGbDvHIgSW5oYWx0ZTwvc3Ryb25nPjxicj4gQWxzIERpZW5zdGVhbmJpZXRlciBzaW5kIHdpciBmw7xyIGVpZ2VuZSBJbmhhbHRlIGF1ZiBkaWVzZXIgU2VpdGUgdmVyYW50d29ydGxpY2guPGJyPjxzdHJvbmc+RGF0ZW5zY2h1dHo8L3N0cm9uZz48YnI+IERpZXNlIFNlaXRlIGVyaGVidCBrZWluZXJsZWkgcGVyc29uZW5iZXpvZ2VuZSBEYXRlbi4gRXMgd2VyZGVuIGtlaW5lIENvb2tpZXMgZ2VzZXR6dCwga2VpbiBUcmFja2luZyBkdXJjaGdlZsO8aHJ0IHVuZCBrZWluZSBBbmFseXNlZGllbnN0ZSBnZW51dHp0LiA8L2Rpdj48L2Zvb3Rlcj48L2Rpdj48IS0tIGVuZCBwYWdlLWxlZnQgLS0+PGRpdiBpZD0iY2hhdC1tb3VudCI+PC9kaXY+PHNjcmlwdCBzcmM9Ii9hcHAuanMiIGRlZmVyPjwvc2NyaXB0PjwhLS1TU1JfSU5JVElBTF9EQVRBLS0+PHNjcmlwdCBzcmM9Ii9jaGF0LmpzIiBkZWZlcj48L3NjcmlwdD48c2NyaXB0PmRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCdpbXByaW50LWVtYWlsJykudGV4dENvbnRlbnQ9J2VtYWlsQGpvaGFubmVzLXJldXRlci5kZSc7PC9zY3JpcHQ+PC9ib2R5PjwvaHRtbD4K"), c=>c.charCodeAt(0)));
const faviconB64 = null;

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === '/') {
      return new Response(indexHtml, { headers: { 'content-type': 'text/html;charset=utf-8' } });
    }
    if (url.pathname === '/favicon.png' && typeof faviconB64 !== 'undefined' && faviconB64) {
      const img = Uint8Array.from(atob(faviconB64), c => c.charCodeAt(0));
      return new Response(img, { headers: { 'content-type': 'image/png', 'cache-control': 'public, max-age=86400' } });
    }
    if (url.pathname === '/api/list') return serveEvents(env, url);
    if (url.pathname === '/api/theme') return serveTags(env);
    if (url.pathname === '/api/districts') return serveDistricts(env);
    if (url.pathname === '/api/organizer') return serveOrganizers(env);
    if (url.pathname === '/api/info') return serveStats(env);
    if (url.pathname.startsWith('/api/same/')) return serveRecurring(env, url.pathname.split('/').pop());
    if (url.pathname === '/robots.txt') return new Response('User-agent: *\nAllow: /\n', { headers: { 'content-type': 'text/plain;charset=utf-8' } });
    if (url.pathname === '/.well-known/security.txt') return serveSecurityTxt();
    if (url.pathname === '/sitemap.xml') return serveSitemapXml();
    return new Response('Not found', { status: 404 });
  }
};

function decode(s) {
  if (!s) return '';
  return s.replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"')
    .replace(/&#(\d+);/g, (_, n) => String.fromCharCode(n));
}

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'content-type': 'application/json;charset=utf-8', 'access-control-allow-origin': '*' }
  });
}

async function serveEvents(env, url) {
  const p = url.searchParams;
  const page = Math.max(1, parseInt(p.get('page') || '1'));
  const perPage = Math.min(100, Math.max(1, parseInt(p.get('per_page') || '50')));
  const search = p.get('search') || '';
  const tags = p.getAll('tag').filter(Boolean);
  const dateFrom = p.get('date_from') || '';
  const organizer = p.get('organizer') || '';

  const db = env.STUTENSEE_DB;
  const wheres = ["tags != 'blocked'"];
  const args = [];

  if (dateFrom) { wheres.push("date_start >= ?"); args.push(dateFrom); }
  if (search) { wheres.push("(title LIKE ? OR location LIKE ? OR organizer LIKE ?)"); args.push(`%${search}%`, `%${search}%`, `%${search}%`); }
  for (const t of tags) { wheres.push("tags LIKE ?"); args.push(`%${t}%`); }
  if (organizer) { wheres.push("organizer = ?"); args.push(organizer); }
  if (p.get('hide_recurring')) { wheres.push("recurring_group_id IS NULL"); }

  const where = wheres.length ? 'WHERE ' + wheres.join(' AND ') : '';
  const offset = (page - 1) * perPage;

  const total = (await db.prepare(`SELECT COUNT(*) as c FROM curated_events ${where}`).bind(...args).first()).c;
  const { results } = await db.prepare(
    `SELECT id, title, date_start, date_end, time_raw, location, organizer, description, event_url, sources, tags, recurring_group_id
     FROM curated_events ${where} ORDER BY date_start ASC, id LIMIT ? OFFSET ?`
  ).bind(...args, perPage, offset).all();

  return json({
    events: results.map(r => ({
      id: r.id, title: decode(r.title), date_start: r.date_start || '', date_end: r.date_end,
      time_raw: r.time_raw, location: decode(r.location), organizer: decode(r.organizer),
      description: decode(r.description), event_url: decode(r.event_url || ''),
      sources: decode(r.sources || ''), tags: r.tags || '',
      recurring_group_id: r.recurring_group_id,
    })),
    total, page, per_page: perPage,
    total_pages: Math.ceil(total / perPage),
  });
}

async function serveOrganizers(env) {
  const { results } = await env.STUTENSEE_DB.prepare(
    "SELECT DISTINCT organizer FROM curated_events WHERE organizer IS NOT NULL AND organizer != '' AND tags != 'blocked' ORDER BY organizer"
  ).all();
  return json(results.map(r => decode(r.organizer)));
}

async function serveTags(env) {
  const themeKeys = new Set(['Sport','Musik','Kultur','Kirche','Kinder','Fest','Markt','Workshop','Bildung','Natur','Senioren','Digital','Handwerk','Essen','Treff','Politik','Verein','Wohltätigkeit','Sonstiges']);
  const { results } = await env.STUTENSEE_DB.prepare(
    "SELECT DISTINCT tags FROM curated_events WHERE tags IS NOT NULL AND tags != '' AND tags != 'blocked'"
  ).all();
  const set = new Set();
  for (const r of results) {
    for (const t of r.tags.split(',')) { const s = t.trim(); if (s && themeKeys.has(s)) set.add(s); }
  }
  return json([...set].sort());
}

async function serveDistricts(env) {
  const themeKeys = new Set(['Sport','Musik','Kultur','Kirche','Kinder','Fest','Markt','Workshop','Bildung','Natur','Senioren','Digital','Handwerk','Essen','Treff','Politik','Verein','Wohltätigkeit','Sonstiges']);
  const { results } = await env.STUTENSEE_DB.prepare(
    "SELECT DISTINCT tags FROM curated_events WHERE tags IS NOT NULL AND tags != '' AND tags != 'blocked'"
  ).all();
  const set = new Set();
  for (const r of results) {
    for (const t of r.tags.split(',')) { const s = t.trim(); if (s && !themeKeys.has(s)) set.add(s); }
  }
  return json([...set].sort());
}

async function serveStats(env) {
  const [raw, curated] = await Promise.all([
    env.STUTENSEE_DB.prepare('SELECT COUNT(*) as c FROM raw_events').first(),
    env.STUTENSEE_DB.prepare('SELECT COUNT(*) as c FROM curated_events').first(),
  ]);
  return json({ raw: raw.c, curated: curated.c });
}

async function serveRecurring(env, groupId) {
  const { results } = await env.STUTENSEE_DB.prepare(
    `SELECT id, title, date_start, date_end, time_raw, location, organizer, substr(description,1,300) as description,
            event_url, sources, tags, recurring_group_id
     FROM curated_events WHERE recurring_group_id = ? ORDER BY date_start`
  ).bind(groupId).all();
  return json(results.map(r => ({
    id: r.id, title: decode(r.title), date_start: r.date_start || '', date_end: r.date_end,
    time_raw: r.time_raw, location: decode(r.location), organizer: decode(r.organizer),
    description: decode(r.description), event_url: decode(r.event_url || ''),
    sources: decode(r.sources || ''), tags: r.tags || '',
    recurring_group_id: r.recurring_group_id,
  })));
}

function serveSecurityTxt() {
  return new Response(`# Security Contact
# If you find a security issue on was-geht-stutensee.de, please report it.
Contact: mailto:email@johannes-reuter.de
Canonical: https://was-geht-stutensee.de/.well-known/security.txt
Preferred-Languages: de, en
Expires: 2027-05-24T14:00:00.000Z
`, {
    headers: { 'content-type': 'text/plain;charset=utf-8', 'cache-control': 'public, max-age=86400' }
  });
}

function serveSitemapXml() {
  return new Response(`<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://was-geht-stutensee.de/</loc>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
</urlset>`, {
    headers: { 'content-type': 'application/xml;charset=utf-8', 'cache-control': 'public, max-age=86400' }
  });
}
