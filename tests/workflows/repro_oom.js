
const targetMB = 4096; // Try to allocate 4GB
console.log(`Starting memory allocation test. Target: ${targetMB} MB`);

try {
    const arrays = [];
    const entrySize = 1024 * 1024; // 1MB strings

    // We'll try to allocate in chunks
    for (let i = 0; i < targetMB; i++) {
        // Allocate 1MB
        arrays.push(new Array(entrySize/8).fill(1.1)); // double is 8 bytes. 1MB / 8 = 128k elements
        if (i % 500 === 0) {
            const used = process.memoryUsage().heapUsed / 1024 / 1024;
            console.log(`Allocated ${i} MB. Heap used: ${Math.round(used)} MB`);
        }
    }
    console.log("Successfully allocated target memory!");
} catch (e) {
    console.error("Allocation failed:", e.message);
    process.exit(1);
}
