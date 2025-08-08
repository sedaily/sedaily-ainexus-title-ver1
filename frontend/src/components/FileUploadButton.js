import React, { useRef, useState, forwardRef, useImperativeHandle } from 'react';
import { PaperClipIcon, DocumentTextIcon, DocumentIcon } from '@heroicons/react/24/outline';
import * as pdfjsLib from 'pdfjs-dist';

// PDF.js worker 설정
pdfjsLib.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version}/pdf.worker.min.js`;

const FileUploadButton = forwardRef(({ onFileContent, disabled }, ref) => {
  const fileInputRef = useRef(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [fileName, setFileName] = useState('');

  // 파일 처리 공통 함수
  const processFile = async (file) => {
    if (!file) return;

    setIsProcessing(true);
    setFileName(file.name);

    try {
      // 파일 크기 체크 (50MB 제한)
      if (file.size > 50 * 1024 * 1024) {
        alert('파일 크기는 50MB를 초과할 수 없습니다.');
        return;
      }

      // 파일 타입별 처리
      if (file.type === 'text/plain' || file.name.endsWith('.txt')) {
        // 텍스트 파일 처리
        const text = await file.text();
        onFileContent(text, {
          fileName: file.name,
          fileType: 'text',
          fileSize: file.size
        });
      } else if (file.type === 'application/pdf' || file.name.endsWith('.pdf')) {
        // PDF 파일 처리
        await handlePdfFile(file);
      } else {
        alert('지원하지 않는 파일 형식입니다. txt, pdf 파일만 업로드 가능합니다.');
        return;
      }
    } catch (error) {
      console.error('파일 처리 오류:', error);
      alert('파일을 처리하는 중 오류가 발생했습니다.');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleFileSelect = async (event) => {
    const file = event.target.files[0];
    if (file) {
      await processFile(file);
      // 같은 파일 재선택 가능하도록 초기화
      event.target.value = '';
    }
  };

  // 외부에서 파일 처리를 위한 메서드 노출
  useImperativeHandle(ref, () => ({
    handleFile: processFile
  }));

  const handlePdfFile = async (file) => {
    try {
      // 클라이언트 사이드에서 PDF.js를 사용한 텍스트 추출
      const arrayBuffer = await file.arrayBuffer();
      const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
      
      let fullText = '';
      const numPages = pdf.numPages;
      
      // 각 페이지에서 텍스트 추출
      for (let pageNum = 1; pageNum <= numPages; pageNum++) {
        const page = await pdf.getPage(pageNum);
        const textContent = await page.getTextContent();
        const pageText = textContent.items.map(item => item.str).join(' ');
        fullText += pageText + '\n\n';
      }
      
      // 추출한 텍스트가 비어있는지 확인
      if (!fullText.trim()) {
        alert('PDF에서 텍스트를 추출할 수 없습니다. 스캔된 이미지 PDF일 수 있습니다.');
        return;
      }
      
      // 추출한 텍스트를 콜백으로 전달
      onFileContent(fullText.trim(), {
        fileName: file.name,
        fileType: 'pdf',
        fileSize: file.size,
        pageCount: numPages
      });
    } catch (error) {
      console.error('PDF 처리 오류:', error);
      
      // 오류 발생 시 서버 API 사용 시도 (fallback)
      try {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch(`${process.env.REACT_APP_API_URL}/extract-text`, {
          method: 'POST',
          body: formData
        });
        
        if (response.ok) {
          const { text } = await response.json();
          onFileContent(text, {
            fileName: file.name,
            fileType: 'pdf',
            fileSize: file.size
          });
        } else {
          alert('PDF 파일 처리 중 오류가 발생했습니다. 텍스트를 직접 복사하여 붙여넣어 주세요.');
        }
      } catch (serverError) {
        alert('PDF 파일 처리 중 오류가 발생했습니다. 텍스트를 직접 복사하여 붙여넣어 주세요.');
      }
    }
  };


  return (
    <div className="relative group">
      <input
        ref={fileInputRef}
        type="file"
        accept=".txt,.pdf"
        onChange={handleFileSelect}
        className="hidden"
        disabled={disabled || isProcessing}
      />
      
      <button
        onClick={() => fileInputRef.current?.click()}
        disabled={disabled || isProcessing}
        className={`p-2 rounded-lg transition-all duration-200 flex items-center justify-center ${
          disabled || isProcessing
            ? 'bg-gray-100 dark:bg-gray-700 text-gray-400 cursor-not-allowed'
            : 'bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-600 dark:text-gray-300 hover:shadow-md'
        }`}
        title={isProcessing ? '파일 처리 중...' : '파일 업로드 (txt, pdf)'}
      >
        {isProcessing ? (
          <div className="animate-spin h-5 w-5 border-2 border-gray-400 border-t-transparent rounded-full" />
        ) : (
          <PaperClipIcon className="h-5 w-5" />
        )}
      </button>

      {/* 호버 시 툴팁 */}
      {!isProcessing && !disabled && (
        <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-1.5 bg-gray-800 dark:bg-gray-700 text-white text-xs rounded-md whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none">
          <div className="text-center">
            <div className="font-medium">파일 업로드</div>
            <div className="text-gray-300 text-[10px]">TXT, PDF (최대 50MB)</div>
          </div>
          <div className="absolute top-full left-1/2 transform -translate-x-1/2 -translate-y-1 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-800 dark:border-t-gray-700"></div>
        </div>
      )}

      {/* 처리 중 상태 표시 */}
      {isProcessing && fileName && (
        <div className="absolute bottom-full left-0 mb-2 px-2 py-1 bg-blue-600 text-white text-xs rounded whitespace-nowrap animate-pulse">
          처리 중: {fileName}
        </div>
      )}
    </div>
  );
});

FileUploadButton.displayName = 'FileUploadButton';

export default FileUploadButton;