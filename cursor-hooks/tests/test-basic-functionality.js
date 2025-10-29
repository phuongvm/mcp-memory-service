/**
 * Basic Functionality Test for Cursor Memory Hooks
 * Tests that core hooks can execute without errors
 */

const path = require('path');
const fs = require('fs');

console.log('🧪 Testing Cursor Memory Hooks\n');

// Test 1: Check file structure
console.log('Test 1: File Structure');
const requiredFiles = [
    'core/agent-start.js',
    'core/agent-complete.js',
    'utilities/cursor-adapter.js',
    'utilities/project-detector.js',
    'utilities/memory-scorer.js',
    'utilities/context-formatter.js',
    'utilities/git-analyzer.js',
    'utilities/mcp-client.js',
    'utilities/memory-client.js',
    'templates/hooks.json.template',
    'templates/config.json.template',
    'README.md'
];

let filesOk = true;
requiredFiles.forEach(file => {
    const filePath = path.join(__dirname, '..', file);
    if (fs.existsSync(filePath)) {
        console.log(`  ✅ ${file}`);
    } else {
        console.log(`  ❌ ${file} - MISSING`);
        filesOk = false;
    }
});

if (!filesOk) {
    console.error('\n❌ File structure test FAILED');
    process.exit(1);
}

console.log('\n✅ File structure test PASSED\n');

// Test 2: Check Node.js syntax
console.log('Test 2: JavaScript Syntax Validation');
const jsFiles = [
    'core/agent-start.js',
    'core/agent-complete.js',
    'utilities/cursor-adapter.js'
];

let syntaxOk = true;
jsFiles.forEach(file => {
    try {
        const filePath = path.join(__dirname, '..', file);
        require(filePath);
        console.log(`  ✅ ${file} - Valid syntax`);
    } catch (error) {
        console.log(`  ❌ ${file} - Syntax error: ${error.message}`);
        syntaxOk = false;
    }
});

if (!syntaxOk) {
    console.error('\n❌ Syntax validation FAILED');
    process.exit(1);
}

console.log('\n✅ Syntax validation PASSED\n');

// Test 3: Check template JSON validity
console.log('Test 3: Template JSON Validation');
const jsonTemplates = [
    'templates/hooks.json.template',
    'templates/config.json.template'
];

let jsonOk = true;
jsonTemplates.forEach(file => {
    try {
        const filePath = path.join(__dirname, '..', file);
        const content = fs.readFileSync(filePath, 'utf8');
        JSON.parse(content);
        console.log(`  ✅ ${file} - Valid JSON`);
    } catch (error) {
        console.log(`  ❌ ${file} - Invalid JSON: ${error.message}`);
        jsonOk = false;
    }
});

if (!jsonOk) {
    console.error('\n❌ JSON validation FAILED');
    process.exit(1);
}

console.log('\n✅ JSON validation PASSED\n');

// Test 4: Check utilities are importable
console.log('Test 4: Utility Module Imports');
const utilities = [
    'project-detector',
    'memory-scorer',
    'context-formatter',
    'git-analyzer',
    'mcp-client',
    'memory-client',
    'cursor-adapter'
];

let importsOk = true;
utilities.forEach(util => {
    try {
        require(path.join(__dirname, '..', 'utilities', `${util}.js`));
        console.log(`  ✅ ${util}.js - Importable`);
    } catch (error) {
        console.log(`  ❌ ${util}.js - Import error: ${error.message}`);
        importsOk = false;
    }
});

if (!importsOk) {
    console.error('\n❌ Utility import test FAILED');
    process.exit(1);
}

console.log('\n✅ Utility import test PASSED\n');

// Summary
console.log('═══════════════════════════════════════');
console.log('🎉 ALL TESTS PASSED');
console.log('═══════════════════════════════════════');
console.log('\n✅ File structure complete');
console.log('✅ JavaScript syntax valid');
console.log('✅ JSON templates valid');
console.log('✅ All utilities importable');
console.log('\n👉 Ready for integration testing!');
console.log('👉 Next: Run installer to set up in a real project\n');

