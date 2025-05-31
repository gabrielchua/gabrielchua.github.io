async function loadMarkdown(path, containerId) {
  const resp = await fetch(path);
  const text = await resp.text();
  const html = marked.parse(text);
  document.getElementById(containerId).innerHTML = html;
}
