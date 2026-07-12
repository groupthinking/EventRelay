// Type augmentation for styled-jsx's `<style jsx>` / `<style jsx global>` syntax.
//
// styled-jsx ships with Next.js but its JSX prop augmentation is not always
// picked up automatically (notably under newer TypeScript / React 19 type
// resolution), causing `Property 'jsx' does not exist on type
// 'StyleHTMLAttributes<...>'` build failures. Declaring it here makes the
// `jsx` and `global` boolean props available on the intrinsic <style> element.
import 'react';

declare module 'react' {
  interface StyleHTMLAttributes<T> extends HTMLAttributes<T> {
    jsx?: boolean;
    global?: boolean;
  }
}
