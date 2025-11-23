document.addEventListener('DOMContentLoaded', () => {
    // This line gets the topic from the HTML, which gets it from the URL
    const quizTopicElement = document.querySelector('h1');
    const quizTopic = quizTopicElement ? quizTopicElement.textContent.replace('Topic Quiz: ', '') : 'General';

    const questionsWrapper = document.getElementById('questions-wrapper');
    const submitQuizBtn = document.getElementById('submitQuizBtn');
    const quizContainer = document.getElementById('quiz-container');
    const resultsContainer = document.getElementById('results-container');
    let quizData = []; // To store the quiz questions and answers

    async function loadQuiz() {
        try {
            const response = await fetch('/generate-quiz', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ topic: quizTopic })
            });
            if (!response.ok) {
                throw new Error(`Server error: ${response.status}`);
            }
            const data = await response.json();
            if (data.quiz) {
                quizData = data.quiz;
                displayQuiz();
            } else { 
                throw new Error('Failed to parse quiz data from AI response.'); 
            }
        } catch (error) {
            questionsWrapper.innerHTML = '<p style="color: red;">Could not load quiz. The AI may be busy. Please try again.</p>';
            console.error("Fetch error:", error);
        }
    }

    function displayQuiz() {
        questionsWrapper.innerHTML = '';
        quizData.forEach((q, index) => {
            const questionDiv = document.createElement('div');
            questionDiv.className = 'quiz-question';
            
            let optionsHTML = '';
            q.options.forEach(option => {
                // Sanitize option value to be used in HTML attributes
                const sanitizedOption = option.replace(/"/g, '&quot;');
                optionsHTML += `<div class="quiz-option"><label><input type="radio" name="question${index}" value="${sanitizedOption}"> ${option}</label></div>`;
            });

            questionDiv.innerHTML = `<p><b>${index + 1}. ${q.question}</b></p><div class="options">${optionsHTML}</div>`;
            questionsWrapper.appendChild(questionDiv);
        });
        submitQuizBtn.classList.remove('hidden');
    }

    submitQuizBtn.addEventListener('click', () => {
        let score = 0;
        quizData.forEach((q, index) => {
            const selectedOption = document.querySelector(`input[name="question${index}"]:checked`);
            if (selectedOption && selectedOption.value === q.answer) {
                score++;
            }
        });
        
        showResults(score, quizData.length);
    });

    function showResults(score, totalQuestions) {
        quizContainer.classList.add('hidden');
        resultsContainer.classList.remove('hidden');

        const percentage = Math.round((score / totalQuestions) * 100);
        const xpGained = score * 50; // 50 XP per correct answer

        resultsContainer.innerHTML = `
            <h1>Quiz Results</h1>
            <div class="dashboard-grid">
                <div class="stat-card"><h3>Your Score</h3><p class="stat-value">${percentage}%</p></div>
                <div class="stat-card"><h3>XP Gained</h3><p class="stat-value">+ ${xpGained} XP</p></div>
                <div class="stat-card"><h3>Correct</h3><p class="stat-value">${score} / ${totalQuestions}</p></div>
            </div>
            <div class="leaderboard" style="margin-top: 20px; text-align: left;">
                <h2>Sample Leaderboard</h2>
                <p>🥇 Alex - 15,200 XP</p>
                <p>🥈 Sarah - 14,850 XP</p>
                <p>🥉 **You - 13,550 XP**</p>
            </div>
            <a href="/dashboard" class="resources-btn" style="margin-top: 20px;">Back to Dashboard</a>
        `;
    }

    loadQuiz(); // Load the quiz when the page opens
});