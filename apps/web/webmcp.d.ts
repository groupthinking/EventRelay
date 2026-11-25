// Type augmentation for Declarative WebMCP `<form toolname tooldescription>` attributes
// (Chrome Early Preview / W3C WebMCP specification).
import 'react';

declare module 'react' {
  interface FormHTMLAttributes<T> extends HTMLAttributes<T> {
    toolname?: string;
    tooldescription?: string;
  }
}
