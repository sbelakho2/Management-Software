// @ts-check
/**
 * ESLint plugin to enforce i18n usage in JSX
 * This prevents hardcoded strings in user-facing components
 */

/** @type {import('eslint').Rule.RuleModule} */
const noHardcodedStrings = {
  meta: {
    type: 'suggestion',
    docs: {
      description: 'Disallow hardcoded strings in JSX - use i18n t() function instead',
      category: 'Best Practices',
      recommended: true,
    },
    messages: {
      hardcodedString: 'Hardcoded string "{{text}}" should use i18n: t(\'{{suggestedKey}}\')',
      hardcodedStringInAttribute: 'Hardcoded string in {{attribute}} attribute should use i18n translation',
    },
    schema: [
      {
        type: 'object',
        properties: {
          // Attributes that should be translated
          translatedAttributes: {
            type: 'array',
            items: { type: 'string' },
            default: [
              'title',
              'placeholder',
              'aria-label',
              'alt',
              'label',
            ],
          },
          // Patterns to ignore (e.g., CSS classes, test IDs)
          ignorePatterns: {
            type: 'array',
            items: { type: 'string' },
            default: [
              '^[a-z-]+$', // kebab-case (CSS classes)
              '^[A-Z_]+$', // CONSTANT_CASE (technical identifiers)
              '^\\d+$', // numbers
              '^\\s*$', // whitespace only
              '^https?://', // URLs
              '^/', // paths
              '^\\./', // relative paths
              '^#', // hex colors or anchors
              '^data-', // data attributes
              '^[a-z]+:', // namespaced attributes
            ],
          },
          // Components to ignore entirely
          ignoreComponents: {
            type: 'array',
            items: { type: 'string' },
            default: ['code', 'pre', 'kbd', 'Script'],
          },
          // Attributes to always ignore
          ignoreAttributes: {
            type: 'array',
            items: { type: 'string' },
            default: [
              'className',
              'class',
              'id',
              'name',
              'type',
              'href',
              'src',
              'key',
              'ref',
              'data-testid',
              'data-state',
              'role',
              'htmlFor',
              'value',
              'defaultValue',
              'icon',
              'variant',
              'size',
              'asChild',
              'side',
              'align',
            ],
          },
        },
        additionalProperties: false,
      },
    ],
  },

  create(context) {
    const options = context.options[0] || {};
    const translatedAttributes = options.translatedAttributes || [
      'title', 'placeholder', 'aria-label', 'alt', 'label',
    ];
    const ignorePatterns = (options.ignorePatterns || []).map(p => new RegExp(p));
    const ignoreComponents = options.ignoreComponents || ['code', 'pre', 'kbd', 'Script'];
    const ignoreAttributes = options.ignoreAttributes || [
      'className', 'class', 'id', 'name', 'type', 'href', 'src', 'key', 'ref',
      'data-testid', 'data-state', 'role', 'htmlFor', 'value', 'defaultValue',
      'icon', 'variant', 'size', 'asChild', 'side', 'align',
    ];

    /**
     * Check if a string should be ignored based on patterns
     * @param {string} text
     * @returns {boolean}
     */
    function shouldIgnore(text) {
      if (!text || typeof text !== 'string') return true;
      const trimmed = text.trim();
      if (!trimmed || trimmed.length === 0) return true;
      
      // Ignore single characters
      if (trimmed.length === 1) return true;
      
      // Ignore pure numbers or technical identifiers
      if (/^[\d.,]+$/.test(trimmed)) return true;
      if (/^[a-z][a-z0-9]*(-[a-z0-9]+)*$/.test(trimmed)) return true; // kebab-case
      
      return ignorePatterns.some(pattern => pattern.test(trimmed));
    }

    /**
     * Generate a suggested i18n key from text
     * @param {string} text
     * @returns {string}
     */
    function suggestKey(text) {
      const cleaned = text
        .toLowerCase()
        .replace(/[^a-z0-9\s]/g, '')
        .trim()
        .split(/\s+/)
        .slice(0, 4)
        .join('.');
      return `common.${cleaned || 'text'}`;
    }

    /**
     * Check if we're inside an ignored component
     * @param {import('eslint').Rule.Node} node
     * @returns {boolean}
     */
    function isInsideIgnoredComponent(node) {
      let parent = node.parent;
      while (parent) {
        if (
          parent.type === 'JSXElement' &&
          parent.openingElement &&
          parent.openingElement.name
        ) {
          const name = parent.openingElement.name.name;
          if (ignoreComponents.includes(name)) {
            return true;
          }
        }
        parent = parent.parent;
      }
      return false;
    }

    return {
      // Check JSX text content
      JSXText(node) {
        const text = node.value;
        if (shouldIgnore(text)) return;
        if (isInsideIgnoredComponent(node)) return;
        
        // Only report if it looks like user-facing text
        if (/[A-Z]/.test(text) || /\s/.test(text.trim())) {
          context.report({
            node,
            messageId: 'hardcodedString',
            data: {
              text: text.trim().slice(0, 30) + (text.trim().length > 30 ? '...' : ''),
              suggestedKey: suggestKey(text),
            },
          });
        }
      },

      // Check JSX attribute values
      JSXAttribute(node) {
        const attrName = node.name && node.name.name;
        if (!attrName) return;
        
        // Skip ignored attributes
        if (ignoreAttributes.includes(attrName)) return;
        if (attrName.startsWith('on')) return; // event handlers
        if (attrName.startsWith('data-')) return; // data attributes
        
        // Only check specific attributes for translation
        if (!translatedAttributes.includes(attrName)) return;
        
        // Check literal string values
        if (node.value && node.value.type === 'Literal' && typeof node.value.value === 'string') {
          const text = node.value.value;
          if (shouldIgnore(text)) return;
          
          context.report({
            node,
            messageId: 'hardcodedStringInAttribute',
            data: { attribute: attrName },
          });
        }
      },

      // Check string literals in JSX expressions
      'JSXExpressionContainer > Literal'(node) {
        if (typeof node.value !== 'string') return;
        if (shouldIgnore(node.value)) return;
        if (isInsideIgnoredComponent(node)) return;
        
        // Check if parent is an ignored attribute
        const parent = node.parent;
        if (parent && parent.parent && parent.parent.type === 'JSXAttribute') {
          const attrName = parent.parent.name && parent.parent.name.name;
          if (ignoreAttributes.includes(attrName)) return;
          if (!translatedAttributes.includes(attrName)) return;
        }
        
        context.report({
          node,
          messageId: 'hardcodedString',
          data: {
            text: node.value.slice(0, 30) + (node.value.length > 30 ? '...' : ''),
            suggestedKey: suggestKey(node.value),
          },
        });
      },
    };
  },
};

module.exports = {
  rules: {
    'no-hardcoded-strings': noHardcodedStrings,
  },
  configs: {
    recommended: {
      plugins: ['i18n-guard'],
      rules: {
        'i18n-guard/no-hardcoded-strings': 'warn',
      },
    },
  },
};
