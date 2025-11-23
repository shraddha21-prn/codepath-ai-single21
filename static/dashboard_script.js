document.addEventListener('DOMContentLoaded', () => {
    // --- Clock Feature ---
    const timeElement = document.getElementById('currentTime');
    if (timeElement) {
        function updateTime() {
            timeElement.textContent = new Date().toLocaleTimeString('en-US');
        }
        setInterval(updateTime, 1000);
        updateTime();
    }

    // --- Skill Analytics Chart ---
    const ctx = document.getElementById('skillRadarChart').getContext('2d');
    new Chart(ctx, {
        type: 'radar', // A radar chart is great for showing skill balance
        data: {
            labels: ['Python', 'SQL', 'Data Cleaning', 'Statistics', 'Excel', 'Communication'],
            datasets: [{
                label: 'Your Skill Level',
                // This is sample data. In a real app, this would come from the database.
                data: [85, 75, 70, 65, 90, 80],
                fill: true,
                backgroundColor: 'rgba(54, 162, 235, 0.2)',
                borderColor: 'rgb(54, 162, 235)',
                pointBackgroundColor: 'rgb(54, 162, 235)',
                pointBorderColor: '#fff',
                pointHoverBackgroundColor: '#fff',
                pointHoverBorderColor: 'rgb(54, 162, 235)'
            }]
        },
        options: {
            elements: {
                line: {
                    borderWidth: 3
                }
            },
            scales: {
                r: {
                    angleLines: { display: false },
                    suggestedMin: 0,
                    suggestedMax: 100
                }
            }
        }
    });
});