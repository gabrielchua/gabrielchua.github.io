fetch('posts.json')
  .then(resp => resp.json())
  .then(posts => {
    const list = document.getElementById('posts-list');
    posts.forEach(p => {
      const li = document.createElement('li');
      li.className = 'list-group-item';
      li.innerHTML = `<a href="${p.path}">${p.title}</a>`;
      list.appendChild(li);
    });
  });
