/**
 * LanguageContext
 * Provides UI language state and translation function
 */

import { createContext, useContext, useState, useEffect } from 'react';
import { getTranslation } from '../utils/translations';

const LanguageContext = createContext();

const STORAGE_KEY = 'ai-group-chat-language';

export const LanguageProvider = ({ children }) => {
  // Load language from localStorage or default to english
  const [language, setLanguageState] = useState(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    return saved || 'english';
  });

  // Save language to localStorage whenever it changes
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, language);
  }, [language]);

  // Translation function
  const t = (key) => {
    return getTranslation(language, key);
  };

  // Toggle language between english and korean
  const toggleLanguage = () => {
    setLanguageState(prev => prev === 'english' ? 'korean' : 'english');
  };

  // Set specific language
  const setLanguage = (lang) => {
    if (lang === 'english' || lang === 'korean') {
      setLanguageState(lang);
    }
  };

  const value = {
    language,
    setLanguage,
    toggleLanguage,
    t,
  };

  return (
    <LanguageContext.Provider value={value}>
      {children}
    </LanguageContext.Provider>
  );
};

// Custom hook to use language context
export const useLanguage = () => {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useLanguage must be used within a LanguageProvider');
  }
  return context;
};

export default LanguageContext;

