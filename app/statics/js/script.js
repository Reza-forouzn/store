document.getElementById('addRowForm').addEventListener('submit', function (event) {
    event.preventDefault();

    const formData = new FormData(this);
    const data = {
        table_name: formData.get('table_name'),
        name: formData.get('name'),
        exp_date: formData.get('exp_date'),
        owner: formData.get('owner'),
        watchers: formData.get('watchers').split(',').map(watcher => watcher.trim()),
        comment: formData.get('comment')
    };

    fetch('/add_row', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
    })
    .then(response => response.json())
    .then(data => {
        alert(data.message || 'Error: ' + data.error);
    })
    .catch(error => {
        alert('Error: ' + error);
    });
});
