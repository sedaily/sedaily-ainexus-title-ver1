import { toast } from "react-hot-toast";

/**
 * 텍스트를 클립보드에 복사하는 유틸리티 함수
 * @param {string} text - 복사할 텍스트
 * @param {string} successMessage - 성공 시 표시할 메시지
 * @param {string} errorMessage - 실패 시 표시할 메시지
 * @returns {Promise<boolean>} - 성공 여부
 */
export const copyToClipboard = async (
  text,
  successMessage = "클립보드에 복사되었습니다!",
  errorMessage = "복사에 실패했습니다."
) => {
  try {
    await navigator.clipboard.writeText(text);
    toast.success(successMessage);
    return true;
  } catch (error) {
    console.error("복사 실패:", error);
    toast.error(errorMessage);
    return false;
  }
};

/**
 * 제목만 추출하여 복사하는 함수
 * @param {string} text - 전체 텍스트
 * @returns {Promise<boolean>} - 성공 여부
 */
export const copyTitlesOnly = async (text) => {
  const extractedTitles = extractTitles(text);
  const textToCopy =
    extractedTitles.length > 0 ? extractedTitles.join("\n") : text;
  return copyToClipboard(textToCopy, "제목이 클립보드에 복사되었습니다!");
};

/**
 * 텍스트에서 제목을 추출하는 함수
 * @param {string} text - 원본 텍스트
 * @returns {Array<string>} - 추출된 제목 배열
 */
export const extractTitles = (text) => {
  const titles = [];

  // 1. 번호 형식: "1. [제목]"
  const numberedMatches = text.match(/^\d+\.\s+(.+?)(?=\n\s*-|$)/gm);
  if (numberedMatches) {
    numberedMatches.forEach((match) => {
      const title = match.replace(/^\d+\.\s+/, "").trim();
      if (title && !title.includes("품질 평가")) {
        titles.push(title);
      }
    });
  }

  // 2. Bullet 형식: "• [제목]"
  if (titles.length === 0) {
    const bulletMatches = text.match(/• "([^"]+)"/g);
    if (bulletMatches) {
      bulletMatches.forEach((match) => {
        const title = match.replace(/• "(.+)"/, "$1").trim();
        if (title) {
          titles.push(title);
        }
      });
    }
  }

  // 3. 일반 Bullet 형식
  if (titles.length === 0) {
    const simpleBulletMatches = text.match(/• ([^\n]+)/g);
    if (simpleBulletMatches) {
      simpleBulletMatches.forEach((match) => {
        const title = match.replace("• ", "").trim();
        if (title && !title.includes("이유:") && title.length < 100) {
          titles.push(title);
        }
      });
    }
  }

  return titles;
};
