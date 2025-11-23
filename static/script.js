
document.addEventListener('DOMContentLoaded', () => {
    // --- Onboarding Logic ---
    const userChoices = { careerPath: '', skillLevel: '' };
    const step1 = document.getElementById('step1');
    const step2 = document.getElementById('step2');
    const step3 = document.getElementById('step3');

    if (step1 && step2 && step3) {
        step1.querySelectorAll('.option-btn').forEach(button => {
            button.addEventListener('click', () => {
                userChoices.careerPath = button.dataset.value;
                step1.classList.add('hidden');
                step2.classList.remove('hidden');
            });
        });

        step2.querySelectorAll('.option-btn').forEach(button => {
            button.addEventListener('click', () => {
                userChoices.skillLevel = button.dataset.value;
                step2.classList.add('hidden');
                step3.classList.remove('hidden');
                fetchRoadmap();
            });
        });
    }

    async function fetchRoadmap() {
        const roadmapResultDiv = document.getElementById('roadmapResult');
        roadmapResultDiv.innerHTML = '<p class="loading">Generating your plan...</p>';

        try {
            const response = await fetch('/generate-roadmap', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(userChoices),
            });

            if (!response.ok) { throw new Error('The server responded with an error.'); }

            const data = await response.json();
            roadmapResultDiv.innerHTML = '';

            if (data.roadmap) {
                // --- THIS IS THE FIX ---
                // Check if data.roadmap is an array. If not, create an array containing the single object.
                const roadmapItems = Array.isArray(data.roadmap) ? data.roadmap : [data.roadmap];
                
                // Now, loop over 'roadmapItems', which is guaranteed to be an array.
                roadmapItems.forEach(item => {
                    const itemDiv = document.createElement('div');
                    itemDiv.className = 'roadmap-item';

                    const weekElement = document.createElement('h3');
                    weekElement.textContent = item.week;

                    const topicsElement = document.createElement('p');
                    topicsElement.textContent = item.topics;

                    const resourcesBtn = document.createElement('button');
                    resourcesBtn.textContent = 'Get Resources';
                    resourcesBtn.className = 'resources-btn';

                    resourcesBtn.addEventListener('click', () => {
                        window.location.href = `/resources?topic=${encodeURIComponent(item.topics)}`;
                    });

                    itemDiv.appendChild(weekElement);
                    itemDiv.appendChild(topicsElement);
                    itemDiv.appendChild(resourcesBtn);
                    
                    roadmapResultDiv.appendChild(itemDiv);
                });
                 // --- END OF FIX ---

            } else {
                 throw new Error('Roadmap data is not in the expected format.');
            }

        } catch (error) {
            roadmapResultDiv.innerHTML = '<p>Sorry, an error occurred. Please check the Console (F12) and the backend terminal for more details.</p>';
            console.error('Error fetching roadmap:', error);
        }
    }
});