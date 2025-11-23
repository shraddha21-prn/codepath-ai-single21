document.addEventListener('DOMContentLoaded', () => {
    // --- Clock Feature ---
    const timeElement = document.getElementById('currentTime');
    if (timeElement) {
        function updateTime() { timeElement.textContent = new Date().toLocaleTimeString('en-US'); }
        setInterval(updateTime, 1000);
        updateTime();
    }

    // --- Interview Page Logic ---
    const step1 = document.getElementById('interview-step1');
    const step2 = document.getElementById('interview-step2');
    const step3 = document.getElementById('interview-step3');
    const getQuestionBtn = document.getElementById('getQuestionBtn');
    const getFeedbackBtn = document.getElementById('getFeedbackBtn');
    const questionResultDiv = document.getElementById('questionResult');
    const feedbackResultDiv = document.getElementById('feedbackResult');
    let currentQuestion = ''; // Variable to store the current question

    // Event listener to get a question from the AI
    getQuestionBtn.addEventListener('click', async () => {
        questionResultDiv.innerHTML = '<p class="loading">Getting a question from the AI...</p>';
        step1.classList.add('hidden');
        step2.classList.remove('hidden');

        try {
            const response = await fetch('/get-interview-question', { method: 'POST' });
            const data = await response.json();
            if (response.ok) {
                currentQuestion = data.question; // Store the question
                questionResultDiv.innerHTML = `<p>${currentQuestion}</p>`;
            } else { throw new Error(data.error); }
        } catch (error) {
            questionResultDiv.innerHTML = `<p>Error getting question. Please try again.</p>`;
            console.error(error);
        }
    });

    // Event listener to get REAL feedback from the AI
    getFeedbackBtn.addEventListener('click', async () => {
        const userAnswer = document.getElementById('answerInput').value;
        step2.classList.add('hidden');
        step3.classList.remove('hidden');
        feedbackResultDiv.innerHTML = '<p class="loading">AI is analyzing your answer...</p>';

        try {
            const response = await fetch('/get-interview-feedback', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    question: currentQuestion,
                    answer: userAnswer
                })
            });
            const data = await response.json();
            if (response.ok) {
                feedbackResultDiv.innerHTML = `<p>${data.feedback}</p>`;
            } else { throw new Error(data.error); }
        } catch (error) {
            feedbackResultDiv.innerHTML = `<p>Error getting feedback. Please try again.</p>`;
            console.error(error);
        }
    });
});