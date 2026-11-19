import { useState } from 'react';

export const useDragDrop = (onSectionReorder, onQuestionReorder) => {
  const [draggedSection, setDraggedSection] = useState(null);
  const [draggedQuestion, setDraggedQuestion] = useState(null);
  const [dragOverSection, setDragOverSection] = useState(null);
  const [dragOverQuestion, setDragOverQuestion] = useState(null);

  const handleSectionDragStart = (e, section) => {
    setDraggedSection(section);
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleSectionDragOver = (e, section) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    setDragOverSection(section.id);
  };

  const handleSectionDragLeave = () => {
    setDragOverSection(null);
  };

  const handleSectionDrop = async (e, targetSection) => {
    e.preventDefault();

    if (!draggedSection || draggedSection.id === targetSection.id) {
      setDraggedSection(null);
      setDragOverSection(null);
      return;
    }

    await onSectionReorder(draggedSection.id, targetSection.order_index);

    setDraggedSection(null);
    setDragOverSection(null);
  };

  const handleQuestionDragStart = (e, question, sectionId) => {
    setDraggedQuestion({ ...question, sectionId });
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleQuestionDragOver = (e, question) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    setDragOverQuestion(question.id);
  };

  const handleQuestionDragLeave = () => {
    setDragOverQuestion(null);
  };

  const handleQuestionDrop = async (e, targetQuestion, sectionId) => {
    e.preventDefault();

    if (!draggedQuestion || draggedQuestion.id === targetQuestion.id) {
      setDraggedQuestion(null);
      setDragOverQuestion(null);
      return;
    }

    if (draggedQuestion.sectionId !== sectionId) {
      setDraggedQuestion(null);
      setDragOverQuestion(null);
      return;
    }

    await onQuestionReorder(draggedQuestion.id, targetQuestion.order_index);

    setDraggedQuestion(null);
    setDragOverQuestion(null);
  };

  return {
    draggedSection,
    draggedQuestion,
    dragOverSection,
    dragOverQuestion,
    handleSectionDragStart,
    handleSectionDragOver,
    handleSectionDragLeave,
    handleSectionDrop,
    handleQuestionDragStart,
    handleQuestionDragOver,
    handleQuestionDragLeave,
    handleQuestionDrop,
  };
};
