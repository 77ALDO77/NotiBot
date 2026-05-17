import { Component, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  time: string;
}

@Component({
  selector: 'app-ai-chat',
  imports: [FormsModule],
  templateUrl: './ai-chat.html',
  styleUrl: './ai-chat.scss',
})
export class AiChat {
  protected readonly messages = signal<ChatMessage[]>([
    {
      id: 'm1',
      role: 'assistant',
      content: '¡Hola! Soy NotiBot AI, tu asistente de noticias. Puedo ayudarte a encontrar información, resumir artículos y responder preguntas sobre lo que está pasando en Lima y Callao. ¿En qué puedo ayudarte hoy?',
      time: 'Ahora',
    },
  ]);

  protected readonly prompt = signal('');

  protected sendMessage(): void {
    const text = this.prompt().trim();
    if (!text) return;

    const userMsg: ChatMessage = {
      id: `m${Date.now()}`,
      role: 'user',
      content: text,
      time: 'Ahora',
    };
    this.messages.update(msgs => [...msgs, userMsg]);
    this.prompt.set('');

    setTimeout(() => {
      const reply: ChatMessage = {
        id: `m${Date.now() + 1}`,
        role: 'assistant',
        content: 'Estoy procesando tu consulta sobre "' + text + '". En una versión futura, aquí verás respuestas generadas por IA basadas en las noticias más recientes de Lima y Callao.',
        time: 'Ahora',
      };
      this.messages.update(msgs => [...msgs, reply]);
    }, 800);
  }

  protected handleKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.sendMessage();
    }
  }
}
