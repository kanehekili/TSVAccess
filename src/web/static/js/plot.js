
(function () { $("[data-toggle='back']").tooltip(); });


// Embed the Plotly chart from the graph_json variable
const graphJson = JSON.parse(document.getElementById('graph-data').textContent);

// Render the graph to the div
Plotly.newPlot('plotly-graph', graphJson.data, graphJson.layout).then(function () {
    // Use graphJson.layout.title.text for the title
    const title = graphJson.layout.title?.text || 'Untitled_Chart';
    console.log('Chart title:', title); // Debugging: Check the extracted title

    // Show the download button
    const downloadBtn = document.getElementById('download-btn');
    downloadBtn.style.display = 'block';

    // Handle the button click
    downloadBtn.addEventListener('click', function () {
        // Send the graphJson to the server via Fetch API (POST request)
        fetch('/download_excel', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                graphJson: graphJson  // Send the JSON object to the server
            })
        })
        .then(response => response.blob())  // Expecting a binary file (Excel)
        .then(blob => {
            // Trigger file download
            const filename = title
                .replace(/[<>:"/\\|?*]+/g, '_') // Replace special characters
                .replace(/\s+/g, '_')          // Replace spaces with underscores
                + '.xlsx';
            const link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = filename; // Use the sanitized title as the filename
            link.click();
        })
        .catch(error => {
            console.error('Error:', error);
        });
    });
});
	
