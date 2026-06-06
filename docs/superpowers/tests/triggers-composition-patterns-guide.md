# Trigger acceptance list — composition-patterns-guide

## Should trigger (3+)
1. "Questo componente ha troppi prop booleani, refactor"
2. "Trasformiamo questo in compound component"
3. "Sto facendo prop drilling di 3 livelli, come risolvo"

## Should NOT trigger (3+)
1. "Crea PostCard" → expect rn-add-screen / screenshot-to-page
2. "Promovi PostCard a L2" → expect promote-component
3. "Lint il codebase" → expect lint_skills.py

## Anti-pattern detection (7 things this skill flags)
1. 4+ boolean props on a component → suggest compound or explicit variants.
2. `renderHeader`, `renderXxx` render props → suggest children.
3. Prop drilling 3+ levels → suggest provider lift.
4. `forwardRef` in React 19+ → suggest `ref` as normal prop.
5. `useContext` in React 19+ for conditional access → suggest `use()`.
6. Compound split across colocation levels → suggest unifying.
7. Promotion to L2 at the 2nd use → suggest waiting (Rule of Three).
