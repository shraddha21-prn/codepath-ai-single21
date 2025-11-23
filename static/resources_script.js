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

    // --- Get references to our new sections ---
    const takeQuizBtn = document.getElementById('takeQuizBtn');
    const submitQuizBtn = document.getElementById('submitQuizBtn');
    const quizSection = document.getElementById('quizSection');
    const analysisSection = document.getElementById('analysisSection');
    const resourceList = document.querySelector('.resource-list'); // Get the resource list

    // --- Event Listeners ---

    // When "Test Your Knowledge" is clicked...
    takeQuizBtn.addEventListener('click', () => {
        // HIDE the resources and the quiz button
        resourceList.classList.add('hidden');
        takeQuizBtn.classList.add('hidden');
        // SHOW the quiz section
        quizSection.classList.remove('hidden');
    });

    // When "Submit Quiz" is clicked...
    submitQuizBtn.addEventListener('click', () => {
        // HIDE the quiz section
        quizSection.classList.add('hidden');
        // SHOW the analysis section
        analysisSection.classList.remove('hidden');
        // NOW, draw our charts
        createScoreChart();
        createProgressChart();
    });

    // --- Chart Drawing Functions (using Chart.js) ---
    function createScoreChart() {
        const ctx = document.getElementById('scorePieChart').getContext('2d');
        new Chart(ctx, {
            type: 'pie',
            data: {
                labels: ['Correct Answers', 'Incorrect Answers'],
                datasets: [{
                    label: 'Quiz Score',
                    data: [8, 2], // Sample data: 8 correct, 2 incorrect
                    backgroundColor: ['#2ecc71', '#e74c3c'],
                    hoverOffset: 4
                }]
            }
        });
    }

    function createProgressChart() {
        const ctx = document.getElementById('progressChart').getContext('2d');
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4 (Current)'],
                datasets: [{
                    label: 'Topic Mastery (%)',
                    data: [70, 85, 75, 90], // Sample progress data
                    backgroundColor: '#3498db'
                }]
            },
            options: {
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100
                    }
                }
            }
        });
    }
});