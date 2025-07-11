// 전역 변수
let currentStep = 0;
const totalSteps = 6;

// DOM 요소
const generateBtn = document.getElementById('generateBtn');
const clearBtn = document.getElementById('clearBtn');
const articleInput = document.getElementById('articleInput');
const loadingSection = document.getElementById('loadingSection');
const resultsSection = document.getElementById('resultsSection');
const errorSection = document.getElementById('errorSection');

// 이벤트 리스너
generateBtn.addEventListener('click', generateTitles);
clearBtn.addEventListener('click', clearForm);

// 제목 생성 함수
async function generateTitles() {
    const articleContent = articleInput.value.trim();
    
    if (!articleContent) {
        showError('기사 내용을 입력해주세요.');
        return;
    }
    
    // UI 상태 변경
    showLoading();
    clearError();
    clearResults();
    
    // 진행 상황 시뮬레이션 시작
    simulateProgress();
    
    try {
        const response = await fetch('/generate-titles', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ article: articleContent })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || '제목 생성 중 오류가 발생했습니다.');
        }
        
        const data = await response.json();
        
        // 결과 표시
        displayResults(data);
        
    } catch (error) {
        showError(error.message);
    } finally {
        hideLoading();
        currentStep = 0;
    }
}

// 진행 상황 시뮬레이션
function simulateProgress() {
    const steps = ['step1', 'step2', 'step3', 'step4', 'step5', 'step6'];
    
    const interval = setInterval(() => {
        if (currentStep < totalSteps) {
            const stepElement = document.getElementById(steps[currentStep]);
            stepElement.classList.add('active');
            currentStep++;
        } else {
            clearInterval(interval);
        }
    }, 500);
}

// 결과 표시
function displayResults(data) {
    // 제목 카테고리별 표시
    displayTitleCategory('journalism-titles', data.titles.journalism);
    displayTitleCategory('balanced-titles', data.titles.balanced);
    displayTitleCategory('click-titles', data.titles.click);
    displayTitleCategory('seo-titles', data.titles.seo);
    displayTitleCategory('social-titles', data.titles.social);
    
    // 최종 추천 제목 표시
    const finalTitleElement = document.getElementById('final-title');
    finalTitleElement.innerHTML = `
        <div class="final-title-content">
            <h4>${data.final_recommendation.title}</h4>
            <p class="title-type">유형: ${data.final_recommendation.type}</p>
            <p class="recommendation-reason">${data.final_recommendation.reason}</p>
        </div>
    `;
    
    resultsSection.style.display = 'block';
}

// 제목 카테고리 표시
function displayTitleCategory(elementId, titles) {
    const container = document.getElementById(elementId);
    container.innerHTML = '';
    
    titles.forEach((item, index) => {
        const titleElement = document.createElement('div');
        titleElement.className = 'title-item';
        
        const evaluationHtml = item.evaluation ? `
            <div class="evaluation">
                <span class="eval-item ${getEvaluationClass(item.evaluation.clarity)}">명확성: ${item.evaluation.clarity}</span>
                <span class="eval-item ${getEvaluationClass(item.evaluation.readability)}">가독성: ${item.evaluation.readability}</span>
                <span class="eval-item ${getEvaluationClass(item.evaluation.clickability)}">클릭유도성: ${item.evaluation.clickability}</span>
                <span class="eval-item ${getEvaluationClass(item.evaluation.factuality)}">사실성: ${item.evaluation.factuality}</span>
                <span class="eval-item ${getEvaluationClass(item.evaluation.stylebook)}">스타일북: ${item.evaluation.stylebook}</span>
            </div>
        ` : '';
        
        titleElement.innerHTML = `
            <h4>${index + 1}. ${item.title}</h4>
            ${evaluationHtml}
            <button class="copy-btn" onclick="copyTitle('${item.title.replace(/'/g, "\\'")}')">복사</button>
        `;
        
        container.appendChild(titleElement);
    });
}

// 평가 등급에 따른 클래스 반환
function getEvaluationClass(evaluation) {
    if (evaluation === '아주 우수') return 'excellent';
    if (evaluation === '보통') return 'good';
    return 'needs-improvement';
}

// 제목 복사
function copyTitle(title) {
    navigator.clipboard.writeText(title).then(() => {
        showNotification('제목이 복사되었습니다.');
    }).catch(err => {
        showError('복사 중 오류가 발생했습니다.');
    });
}

// 알림 표시
function showNotification(message) {
    const notification = document.createElement('div');
    notification.className = 'notification';
    notification.textContent = message;
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

// 로딩 표시
function showLoading() {
    loadingSection.style.display = 'block';
    resultsSection.style.display = 'none';
    generateBtn.disabled = true;
    
    // 모든 단계 초기화
    document.querySelectorAll('.step').forEach(step => {
        step.classList.remove('active');
    });
}

// 로딩 숨기기
function hideLoading() {
    loadingSection.style.display = 'none';
    generateBtn.disabled = false;
}

// 오류 표시
function showError(message) {
    errorSection.style.display = 'block';
    errorSection.querySelector('.error-message').textContent = message;
}

// 오류 숨기기
function clearError() {
    errorSection.style.display = 'none';
}

// 결과 초기화
function clearResults() {
    resultsSection.style.display = 'none';
}

// 폼 초기화
function clearForm() {
    articleInput.value = '';
    clearResults();
    clearError();
}