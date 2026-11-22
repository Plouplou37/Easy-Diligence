import { useEffect, useRef } from 'react';

// Every window of the application in this browser listens on this channel:
// when an answer changes in one, the others fetch it again.
const CHANNEL = 'easy-diligence-answers';
const TYPE = 'answer-changed';

const supported = typeof window !== 'undefined' && 'BroadcastChannel' in window;

// This window's mark on what it sends. A channel never receives its own
// messages, but the channel that sends and the ones that listen are separate
// channels of the same window: without the mark, a window would hear itself.
const WINDOW_ID = `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;

// One channel to send with, opened on first use and kept with the window.
let sender = null;

/** Tells the other windows that an answer of a session changed. */
export const publishAnswerChange = ({ sessionId, answerId }) => {
  if (!supported) return;
  try {
    sender = sender || new BroadcastChannel(CHANNEL);
    sender.postMessage({ type: TYPE, from: WINDOW_ID, sessionId, answerId });
  } catch {
    // Not delivered: the other windows show the change on their next load.
  }
};

/**
 * Calls `handler({ sessionId, answerId })` when another window changed an
 * answer. The handler of the latest render is the one called, so it reads the
 * current state. Nothing happens where BroadcastChannel does not exist.
 */
export const useAnswerChanges = handler => {
  const handlerRef = useRef(handler);
  useEffect(() => {
    handlerRef.current = handler;
  });

  useEffect(() => {
    if (!supported) return undefined;
    const channel = new BroadcastChannel(CHANNEL);
    channel.onmessage = event => {
      const message = event.data;
      if (!message || message.type !== TYPE || message.from === WINDOW_ID) return;
      handlerRef.current?.({ sessionId: message.sessionId, answerId: message.answerId });
    };
    return () => channel.close();
  }, []);
};
