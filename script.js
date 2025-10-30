// --- 怪物查詢工具的專屬邏輯 ---
function initializeMondexLogic() {
    const loadingIndicator = document.getElementById('loading-indicator');
    const resultsContainer = document.getElementById('results-container');
    const showMapSearchBtn = document.getElementById('show-map-search'), showMonsterSearchBtn = document.getElementById('show-monster-search'), showIdSearchBtn = document.getElementById('show-id-search'), showItemSearchBtn = document.getElementById('show-item-search');
    const mapSearchPanel = document.getElementById('map-search-panel'), monsterSearchPanel = document.getElementById('monster-search-panel'), idSearchPanel = document.getElementById('id-search-panel'), itemSearchPanel = document.getElementById('item-search-panel');
    const mapIdInput = document.getElementById('map-id-input'), mapSearchBtn = document.getElementById('map-search-btn');
    const monsterNameInput = document.getElementById('monster-name-input'), monsterSearchBtn = document.getElementById('monster-search-btn');
    const enemybaseIdInput = document.getElementById('enemybase-id-input'), idSearchBtn = document.getElementById('id-search-btn');
    const itemSearchInput = document.getElementById('item-search-input'), itemSearchBtn = document.getElementById('item-search-btn');
    const catchableFilter = document.getElementById('catchable-filter'), levelOneFilter = document.getElementById('level-one-filter');
    let allData = {}, dataMaps = {};
    function cleanAndConvert(value, toType = 'int') { if (value === null || value === undefined) return null; try { const cleanedStr = String(value).replace(/\s/g, '').trim(); if (toType === 'int') return parseInt(parseFloat(cleanedStr), 10); if (toType === 'float') return parseFloat(cleanedStr); return cleanedStr; } catch (e) { return null; } }
    function preprocessData() { dataMaps.groups = new Map(allData.groups.map(g => [String(cleanAndConvert(g.group_id)), g])); dataMaps.enemies = new Map(allData.enemies.map(e => [String(cleanAndConvert(e.enemy_id)), e])); dataMaps.enemybases = new Map(allData.enemybases.map(b => [String(cleanAndConvert(b.enemybase_id)), b])); dataMaps.enemiesByBaseId = new Map(); allData.enemies.forEach(enemy => { const baseId = String(cleanAndConvert(enemy.enemybase_id)); if (!baseId) return; if (!dataMaps.enemiesByBaseId.has(baseId)) { dataMaps.enemiesByBaseId.set(baseId, []); } dataMaps.enemiesByBaseId.get(baseId).push(enemy); }); }
    async function loadAllData() { loadingIndicator.style.display = 'block'; resultsContainer.innerHTML = ''; const dataFiles = { encounts: './pages/monsters/data/encounts.json', groups: './pages/monsters/data/groups.json', enemies: './pages/monsters/data/enemies.json', enemybases: './pages/monsters/data/enemybases.json', maps: './pages/monsters/data/maps.json', items: './pages/monsters/data/items.json' }; try { const responses = await Promise.all(Object.values(dataFiles).map(file => fetch(file))); const jsonData = await Promise.all(responses.map(res => res.json())); Object.keys(dataFiles).forEach((key, index) => { allData[key] = jsonData[index]; }); preprocessData(); console.log("所有資料載入並預處理成功!"); loadingIndicator.style.display = 'none'; } catch (error) { console.error("載入資料時發生錯誤:", error); loadingIndicator.innerHTML = '<p style="color: red;">資料載入失敗，請檢查檔案或網路連線。</p>'; } }
    function generateDropHtml(enemy, highlightItemIds = []) { let dropList = []; for (let i = 1; i <= 10; i++) { const itemId = cleanAndConvert(enemy[`drop_item${i}`]); const itemRate = cleanAndConvert(enemy[`drop_rate${i}`]); if (itemId && itemId > 0) { dropList.push({ id: itemId, rate: itemRate || 0 }); } } if (dropList.length === 0) return '無掉落物'; const dropHtmlElements = dropList.map(item => { const itemName = allData.items[item.id] || '未知物品'; const ratePercent = ((item.rate || 0) / 1000 * 100).toFixed(1); const fullText = `${itemName}(${item.id}) <span style="color: #ADD8E6;">[${ratePercent}%]</span>`; if (highlightItemIds.includes(item.id)) { return `<span class="item-highlight">${fullText}</span>`; } else { return fullText; } }); return dropHtmlElements.join(', '); }
    function performMapSearch() { resultsContainer.innerHTML = ''; const searchTerm = mapIdInput.value.trim(); if (!searchTerm) { resultsContainer.innerHTML = '<p>請輸入地圖 ID 或 名稱。</p>'; return; } let targetMapIds = []; if (!isNaN(searchTerm) && searchTerm !== '') { targetMapIds.push(cleanAndConvert(searchTerm)); } else { targetMapIds = Object.entries(allData.maps).filter(([id, name]) => name.includes(searchTerm)).map(([id, name]) => parseInt(id)); } if (targetMapIds.length === 0) { resultsContainer.innerHTML = `<p>找不到符合「${searchTerm}」的地圖。</p>`; return; } let htmlResult = ''; targetMapIds.forEach(mapId => { const mapName = allData.maps[mapId] || "未知地圖"; htmlResult += `<div class="map-result"><h3>查詢地圖: ${mapName}(${mapId})</h3>`; const encountsOnMap = allData.encounts.filter(e => cleanAndConvert(e.map_id) === mapId); if (encountsOnMap.length === 0) { htmlResult += `<p>此地圖沒有遇敵資料。</p>`; } else { encountsOnMap.forEach(enc => { const x1 = cleanAndConvert(enc.x1), y1 = cleanAndConvert(enc.y1), x2 = cleanAndConvert(enc.x2), y2 = cleanAndConvert(enc.y2); let areaHasResults = false; let areaHtml = `<div class="enc-area"><h4>地圖區域: (${x1}, ${y1}) - (${x2}, ${y2})</h4>`; let groupsWithRates = []; for (let i = 1; i <= 10; i++) { const groupId = cleanAndConvert(enc[`group${i}`]); const groupRate = cleanAndConvert(enc[`group_rate${i}`]); if (groupId && groupId > 0) { groupsWithRates.push({ id: groupId, rate: groupRate || 0 }); } } const totalRate = groupsWithRates.reduce((sum, g) => sum + g.rate, 0); groupsWithRates.forEach(groupData => { const gid = groupData.id; const group = dataMaps.groups.get(String(gid)); if (!group) return; let groupHasResults = false; let conditionText = ""; const itemNeededId = cleanAndConvert(group.item_needed), itemAvoidId = cleanAndConvert(group.item_avoid); if (itemNeededId !== -1) conditionText = ` (需求: ${allData.items[itemNeededId] || '未知'}(${itemNeededId}))`; if (itemAvoidId !== -1) conditionText = ` (迴避: ${allData.items[itemAvoidId] || '未知'}(${itemAvoidId}))`; let percentageText = ""; if (totalRate > 0 && groupData.rate > 0) { const percentage = (groupData.rate / totalRate * 100).toFixed(1); percentageText = ` <span style="color: #FFD700;">[${percentage}%]</span>`; } let groupHtml = `<div class="group-block"><h5> -> 怪物組: ${gid}${percentageText}${conditionText}</h5>`; const petIds = Object.keys(group).filter(k => k.startsWith('pet_id')).map(k => cleanAndConvert(group[k])).filter(id => id && id > 0); petIds.forEach(pid => { const enemy = dataMaps.enemies.get(String(pid)); if (!enemy) return; if (catchableFilter.checked && cleanAndConvert(enemy.catchable) !== 1) return; if (levelOneFilter.checked && cleanAndConvert(enemy.max_level) !== 1) return; groupHasResults = true; const base = dataMaps.enemybases.get(String(enemy.enemybase_id)); if (!base) return; const dropText = generateDropHtml(enemy); const catchableText = cleanAndConvert(enemy.catchable) === 1 ? '可' : '不可'; const lvl_min = cleanAndConvert(enemy.min_level), lvl_max = cleanAndConvert(enemy.max_level); groupHtml += `<div class="monster-details"><p><strong>* <span class="monster-name">${base.monster_name}</span></strong></p><p class="info-line">- 等級: <span class="level-highlight">${lvl_min} - ${lvl_max}</span></p><p class="info-line">- 可否捕捉: ${catchableText}</p><p class="info-line">- 掉落物: ${dropText}</p></div>`; }); if (groupHasResults) { areaHasResults = true; groupHtml += `</div>`; areaHtml += groupHtml; } }); if (areaHasResults) { areaHtml += `</div>`; htmlResult += areaHtml; } }); } htmlResult += `</div>`; }); resultsContainer.innerHTML = htmlResult; }
    function renderMonsterResults(baseInfos, searchTerm, highlightItemIds = []) { let htmlResult = ''; if (baseInfos.length === 0) { return `<p>資料庫中找不到符合「${searchTerm}」的怪物。</p>`; } let foundAnyEncounterable = false; baseInfos.forEach(base => { let monsterHtml = ''; let printedHeader = false; const baseId = cleanAndConvert(base.enemybase_id); let enemies = dataMaps.enemiesByBaseId.get(String(baseId)) || []; const isCatchable = catchableFilter.checked; const isLevelOne = levelOneFilter.checked; const isItemSearchMode = showItemSearchBtn.classList.contains('active'); if (isLevelOne) { enemies = enemies.filter(e => cleanAndConvert(e.max_level) === 1); } if (isCatchable && !isItemSearchMode) { enemies = enemies.filter(e => cleanAndConvert(e.catchable) === 1); } enemies.forEach(enemy => { const enemyId = cleanAndConvert(enemy.enemy_id); const petIdCols = Array.from({length: 10}, (_, i) => `pet_id${i + 1}`); const containingGroups = allData.groups.filter(g => petIdCols.some(col => cleanAndConvert(g[col]) === enemyId)); if (containingGroups.length > 0) { foundAnyEncounterable = true; if (!printedHeader) { monsterHtml += `<div class="monster-header"><h3><span class="monster-name">${base.monster_name}</span> (圖鑑編號: ${baseId})</h3><p class="monster-header-details ability-line">能力: 初始(${cleanAndConvert(base.initial_stats)}) 成長(${cleanAndConvert(base.growth_rate, 'float')}) | 體(${cleanAndConvert(base.hp)}) 腕(${cleanAndConvert(base.str)}) 耐(${cleanAndConvert(base.vit)}) 速(${cleanAndConvert(base.dex)}) | 屬性: 地(${cleanAndConvert(base.earth)}) 水(${cleanAndConvert(base.water)}) 火(${cleanAndConvert(base.fire)}) 風(${cleanAndConvert(base.wind)})</p><p class="monster-header-details resist-line">抗性: 毒(${cleanAndConvert(base.poison_res)}) 麻(${cleanAndConvert(base.paralysis_res)}) 睡(${cleanAndConvert(base.sleep_res)}) 石(${cleanAndConvert(base.stone_res)}) 酒(${cleanAndConvert(base.drunk_res)}) 亂(${cleanAndConvert(base.confuse_res)}) | 其他: 持有(${cleanAndConvert(base.can_hold)}) 蛋群(${cleanAndConvert(base.egg_group)}) 圖號(${cleanAndConvert(base.sprite_id)})</p></div>`; printedHeader = true; } const dropText = generateDropHtml(enemy, highlightItemIds); const catchableText = cleanAndConvert(enemy.catchable) === 1 ? '可' : '不可'; const lvl_min = cleanAndConvert(enemy.min_level), lvl_max = cleanAndConvert(enemy.max_level); monsterHtml += `<div class="monster-version"><p class="info-line">- 等級範圍: <span class="level-highlight">${lvl_min} - ${lvl_max}</span></p><p class="info-line">- 可否捕捉: ${catchableText}</p><p class="info-line">- 掉落物: ${dropText}</p><p class="info-line">- 出沒地點:</p>`; const groupIdCols = Array.from({length: 10}, (_, i) => `group${i + 1}`); containingGroups.forEach(group => { const groupId = cleanAndConvert(group.group_id); let conditionText = ""; const itemNeededId = cleanAndConvert(group.item_needed), itemAvoidId = cleanAndConvert(group.item_avoid); if (itemNeededId !== -1) conditionText = ` (需求: ${allData.items[itemNeededId] || '未知'}(${itemNeededId}))`; if (itemAvoidId !== -1) conditionText = ` (迴避: ${allData.items[itemAvoidId] || '未知'}(${itemAvoidId}))`; const containingEncounts = allData.encounts.filter(enc => groupIdCols.some(col => cleanAndConvert(enc[col]) === groupId)); containingEncounts.forEach(enc => { let groupsWithRates = []; for (let i = 1; i <= 10; i++) { const gId = cleanAndConvert(enc[`group${i}`]); const gRate = cleanAndConvert(enc[`group_rate${i}`]); if (gId && gId > 0) { groupsWithRates.push({ id: gId, rate: gRate || 0 }); } } const totalRate = groupsWithRates.reduce((sum, g) => sum + g.rate, 0); const currentGroupData = groupsWithRates.find(g => g.id === groupId); const currentGroupRate = currentGroupData ? currentGroupData.rate : 0; let percentageText = ""; if (totalRate > 0 && currentGroupRate > 0) { const percentage = (currentGroupRate / totalRate * 100).toFixed(1); percentageText = ` <span style="color: #FFD700;">[${percentage}%]</span>`; } const mapId = cleanAndConvert(enc.map_id); const mapName = allData.maps[mapId] || '地圖'; monsterHtml += `<p class="info-line" style="margin-left: 40px;">- ${mapName}(${mapId}) (${cleanAndConvert(enc.x1)}, ${cleanAndConvert(enc.y1)})-(${cleanAndConvert(enc.x2)}, ${cleanAndConvert(enc.y2)}) [怪物組: ${groupId}${percentageText}${conditionText}]</p>`; }); }); monsterHtml += `</div>`; } }); htmlResult += monsterHtml; }); if (!foundAnyEncounterable && baseInfos.length > 0) { htmlResult = `<p>找到了「${searchTerm}」的怪物基本資料，但牠並未在任何地圖上出現。</p>`; } return htmlResult; }
    function performMonsterSearch() { resultsContainer.innerHTML = ''; const monsterName = monsterNameInput.value.trim(); if (!monsterName) { resultsContainer.innerHTML = '<p>請輸入怪物名稱。</p>'; return; } const baseInfos = allData.enemybases.filter(b => b.monster_name && b.monster_name.includes(monsterName)); resultsContainer.innerHTML = renderMonsterResults(baseInfos, monsterName); }
    function performIdSearch() { resultsContainer.innerHTML = ''; const enemybaseId = cleanAndConvert(enemybaseIdInput.value); if (enemybaseId === null) { resultsContainer.innerHTML = '<p>請輸入有效的圖鑑編號。</p>'; return; } const baseInfos = allData.enemybases.filter(b => cleanAndConvert(b.enemybase_id) === enemybaseId); resultsContainer.innerHTML = renderMonsterResults(baseInfos, `圖鑑編號 ${enemybaseId}`); }
    function performItemSearch() { resultsContainer.innerHTML = ''; const searchTerm = itemSearchInput.value.trim(); if (!searchTerm) { resultsContainer.innerHTML = '<p>請輸入掉落物名稱或物品編號。</p>'; return; } let targetItemIds = []; if (!isNaN(searchTerm) && searchTerm !== '') { targetItemIds.push(cleanAndConvert(searchTerm)); } else { targetItemIds = Object.entries(allData.items).filter(([id, name]) => name.includes(searchTerm)).map(([id, name]) => parseInt(id)); } if (targetItemIds.length === 0) { resultsContainer.innerHTML = `<p>找不到名稱或編號符合「${searchTerm}」的物品。</p>`; return; } const dropCols = Array.from({length: 10}, (_, i) => `drop_item${i + 1}`); const foundEnemies = allData.enemies.filter(enemy => dropCols.some(col => targetItemIds.includes(cleanAndConvert(enemy[col])))); if (foundEnemies.length === 0) { resultsContainer.innerHTML = `<p>沒有怪物會掉落符合「${searchTerm}」的物品。</p>`; return; } const foundEnemybaseIds = [...new Set(foundEnemies.map(enemy => cleanAndConvert(enemy.enemybase_id)))]; const foundBaseInfos = foundEnemybaseIds.map(id => dataMaps.enemybases.get(String(id))).filter(Boolean); resultsContainer.innerHTML = renderMonsterResults(foundBaseInfos, searchTerm, targetItemIds); }
    function setActivePanel(activePanel) { [mapSearchPanel, monsterSearchPanel, idSearchPanel, itemSearchPanel].forEach(p => p.style.display = 'none'); [showMapSearchBtn, showMonsterSearchBtn, showIdSearchBtn, showItemSearchBtn].forEach(b => b.classList.remove('active')); const panels = { 'map': { panel: mapSearchPanel, button: showMapSearchBtn }, 'monster': { panel: monsterSearchPanel, button: showMonsterSearchBtn }, 'id': { panel: idSearchPanel, button: showIdSearchBtn }, 'item': { panel: itemSearchPanel, button: showItemSearchBtn } }; if (panels[activePanel]) { panels[activePanel].panel.style.display = 'flex'; panels[activePanel].button.classList.add('active'); } }
    showMapSearchBtn.addEventListener('click', () => setActivePanel('map')); showMonsterSearchBtn.addEventListener('click', () => setActivePanel('monster')); showIdSearchBtn.addEventListener('click', () => setActivePanel('id')); showItemSearchBtn.addEventListener('click', () => setActivePanel('item'));
    mapSearchBtn.addEventListener('click', performMapSearch); monsterSearchBtn.addEventListener('click', performMonsterSearch); idSearchBtn.addEventListener('click', performIdSearch); itemSearchBtn.addEventListener('click', performItemSearch);
    mapIdInput.addEventListener('keyup', (e) => { if (e.key === 'Enter') performMapSearch(); }); monsterNameInput.addEventListener('keyup', (e) => { if (e.key === 'Enter') performMonsterSearch(); }); enemybaseIdInput.addEventListener('keyup', (e) => { if (e.key === 'Enter') performIdSearch(); }); itemSearchInput.addEventListener('keyup', (e) => { if (e.key === 'Enter') performItemSearch(); });
    loadAllData();
}

// --- 任務查詢工具的專屬邏輯 ---
function initializeQuestLogic() {
    // 獲取 UI 元素
    const areaFilter = document.getElementById('quest-area-filter');
    const seriesFilter = document.getElementById('quest-series-filter');
    const nameInput = document.getElementById('quest-name-input');
    const searchBtn = document.getElementById('quest-search-btn');
    const listContainer = document.getElementById('quest-list-container');
    const guideDisplay = document.getElementById('quest-guide-display');

    let allQuests = []; // 用來儲存從 JSON 載入的所有任務

    // 1. 載入 JSON 資料
    async function loadQuestData() {
        try {
            const response = await fetch('./pages/quests/data/quests.json');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            allQuests = await response.json();
            // 頁面載入時不自動查詢，等待使用者點擊
        } catch (error) {
            console.error("載入任務資料失敗:", error);
            listContainer.innerHTML = '<p style="color: red;">任務資料載入失敗，請檢查 pages/quests/data/quests.json</p>';
        }
    }

    // 2. 執行篩選、排序、並渲染列表
    function performSearch() {
        // 獲取篩選條件
        const selectedArea = areaFilter.value;
        const selectedSeries = seriesFilter.value;
        const searchTerm = nameInput.value.toLowerCase().trim();

        // 進行篩選
        const filteredQuests = allQuests.filter(quest => {
            // 檢查區域 (all 或 包含)
            const matchesArea = (selectedArea === 'all' || quest.area.includes(selectedArea));
            
            // 檢查系列 (all 或 包含)
            // 您的 <option value="完美人"> 對應 "完美人任務"
            const matchesSeries = (selectedSeries === 'all' || quest.series.includes(selectedSeries));
            
            // 檢查名稱 (關鍵字)
            const matchesName = (searchTerm === '' || quest.name.toLowerCase().includes(searchTerm));

            return matchesArea && matchesSeries && matchesName;
        });

        // 依照您的要求，用 "編號" (id_num) 排序
        filteredQuests.sort((a, b) => a.id_num - b.id_num);

        // 渲染列表
        renderList(filteredQuests);
    }

    // 3. 渲染列表 (傳入已篩選的資料)
    function renderList(quests) {
        if (quests.length === 0) {
            listContainer.innerHTML = '<p>找不到符合條件的任務。</p>';
            guideDisplay.innerHTML = '<p>點選左側任務以顯示攻略。</p>'; // 清空攻略區
            return;
        }

        listContainer.innerHTML = quests.map(quest => {
            // 使用 data-id 儲存任務編號，方便點擊時抓取
            return `<div class="quest-item" data-id="${quest.id_num}">
                ${quest.name}
            </div>`;
        }).join('');
        
        // 預設顯示第一筆任務的攻略
        displayGuide(quests[0].id_num);
        // 標記第一項為 .active
        listContainer.querySelector('.quest-item').classList.add('active');
    }

    // 4. 顯示攻略
    function displayGuide(questIdNum) {
        // 轉為數字
        const id = parseInt(questIdNum, 10);
        
        // 從 allQuests 中找到完整的任務資料
        const quest = allQuests.find(q => q.id_num === id);

        if (!quest) {
            guideDisplay.innerHTML = '<p style="color: red;">錯誤：找不到任務資料。</p>';
            return;
        }

        // 組合 HTML 並顯示
        guideDisplay.innerHTML = `
            <h3>${quest.name}</h3>
            <div class="quest-meta-info">
                <p><strong>區域:</strong> ${quest.area}</p>
                <p><strong>限制:</strong> ${quest.limitations}</p>
                <p><strong>任務獎勵:</strong> ${quest.reward_text}</p>
            </div>
            <hr>
            
            <h3>${quest.guide_title}</h3>
            
            <div class="quest-meta-info">
                ${quest.guide_content_html}
            </div>
        `;
        
        // 處理 .active 狀態
        // 移除所有 .active
        listContainer.querySelectorAll('.quest-item').forEach(item => {
            item.classList.remove('active');
        });
        // 為當前點擊的項目添加 .active
        const activeItem = listContainer.querySelector(`.quest-item[data-id="${questIdNum}"]`);
        if (activeItem) {
            activeItem.classList.add('active');
        }
    }

    // 5. 綁定事件
    // "查詢" 按鈕
    searchBtn.addEventListener('click', performSearch);
    
    // 關鍵字輸入框支援 Enter
    nameInput.addEventListener('keyup', (e) => {
        if (e.key === 'Enter') {
            performSearch();
        }
    });

    // 列表點擊 (使用事件委派)
    listContainer.addEventListener('click', (e) => {
        const item = e.target.closest('.quest-item');
        if (item) {
            displayGuide(item.dataset.id);
        }
    });

    // 6. 執行
    loadQuestData();
}


// --- 網站全局導覽邏輯 ---
document.addEventListener('DOMContentLoaded', function () {
    const mainContent = document.querySelector('.main-content');
    const navItems = document.querySelectorAll('.sidebar .nav-item');
    const subMenuParents = document.querySelectorAll('.sidebar .has-children');
    const hamburger = document.querySelector('.hamburger-menu');
    const sidebar = document.querySelector('.sidebar');

    async function loadPage(pagePath) {
        const filePath = `./pages/${pagePath}.html`;
        try {
            const response = await fetch(filePath);
            if (response.ok) {
                mainContent.innerHTML = await response.text();
                
                // 處理怪物查詢工具
                if (pagePath === 'monsters/mondex') {
                    initializeMondexLogic();
                }
                // *** ↓↓↓ 在這裡插入新程式碼 ↓↓↓ ***
                if (pagePath === 'quests/questdex') { // 確保檔名匹配
                    initializeQuestLogic();
                }
                // *** ↑↑↑ 新程式碼結束 ↑↑↑ ***
                // *** 新增的邏輯：檢查地圖模式 ***
                if (pagePath.startsWith('maps/')) {
                    // 檢查頁面是否包含「互動式地圖」的容器
                    if (document.querySelector('.interactive-map-container')) {
                        // 如果是，就初始化「新模式」
                        initializeInteractiveMap();
                    }
                    // 如果沒有，就什麼都不做 (會自動採用 100.html 的舊模式)
                }

            } else {
                mainContent.innerHTML = `<h1>錯誤 404</h1><p>找不到頁面: <code>${filePath}</code></p>`;
            }
        } catch (error) {
            console.error('載入頁面時發生錯誤:', error);
            mainContent.innerHTML = `<h1>載入錯誤</h1><p>無法載入頁面內容。</p>`;
        }
    }
    // --- 互動式地圖 (新模式) 的初始化邏輯 ---
    function initializeInteractiveMap() {
        const svgCanvas = document.getElementById('map-line-svg');
        const labels = document.querySelectorAll('.map-label-list li');
        const mapWrapper = document.querySelector('.map-wrapper');
        const mapDots = document.querySelectorAll('.map-dot');

        if (!svgCanvas || !labels.length || !mapWrapper) {
            console.warn("互動式地圖缺少必要元素 (svgCanvas, labels, mapWrapper)，初始化失敗。");
            return; 
        }

        // 1. 為所有標籤和點建立 SVG 線條
        labels.forEach(label => {
            const targetId = label.dataset.targetId;
            const dot = document.getElementById(targetId);
            if (dot) {
                const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
                line.id = 'line-' + targetId;
                line.classList.add('map-line');
                svgCanvas.appendChild(line);
            }
        });

        // 2. 建立一個函數來更新單一線條的位置 (關鍵)
        function updateLine(label, dot, line) {
            // 取得 mapWrapper 的邊界 (基準點)
            const wrapperRect = mapWrapper.getBoundingClientRect();
            
            // 取得「點」相對於 wrapper 的座標 (即圖示尖端位置)
            const dotX = dot.offsetLeft;
            const dotY = dot.offsetTop;     

            // 取得「標籤」相對於 wrapper 的邊緣座標
            const labelRect = label.getBoundingClientRect();
            
            let labelX;
            // 判斷標籤在左側還右側
            if ((labelRect.left + labelRect.width / 2) < wrapperRect.left) {
                // 標籤在左側，線連到標籤的「右邊緣」
                labelX = labelRect.right - wrapperRect.left;
            } else {
                // 標籤在右側，線連到標籤的「左邊緣」
                labelX = labelRect.left - wrapperRect.left;
            }
            // 線的 Y 軸對齊標籤的中間
            const labelY = (labelRect.top + labelRect.height / 2) - wrapperRect.top;

            // 設定 SVG 線條的起點 (x1, y1) 和終點 (x2, y2)
            line.setAttribute('x1', dotX);
            line.setAttribute('y1', dotY);
            line.setAttribute('x2', labelX);
            line.setAttribute('y2', labelY);
        }

        // 3. 處理點擊事件 (標籤)
        labels.forEach(label => {
            label.addEventListener('click', () => {
                toggleActiveState(label.dataset.targetId);
            });
        });

        // 4. 處理點擊事件 (地圖上的點)
        mapDots.forEach(dot => {
            dot.addEventListener('click', () => {
                toggleActiveState(dot.id);
            });
        });

        // 5. 抽離出共用的切換邏輯
        function toggleActiveState(targetId) {
            const dot = document.getElementById(targetId);
            const line = document.getElementById('line-' + targetId);
            // 找到對應的 label
            const label = document.querySelector(`li[data-target-id="${targetId}"]`);

            if (dot && line && label) {
                // 切換 active 狀態
                label.classList.toggle('active');
                line.classList.toggle('active');

                // 如果是啟動狀態，就更新一次線條位置
                if (label.classList.contains('active')) {
                    updateLine(label, dot, line);
                }
            }
        }

        // 6. (重要) 處理視窗縮放 (使用 Debounce)
        let resizeTimer;
        const debouncedUpdate = () => {
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(() => {
                // 重新計算所有「可見」的線條
                document.querySelectorAll('.map-label-list li.active').forEach(activeLabel => {
                    const targetId = activeLabel.dataset.targetId;
                    const dot = document.getElementById(targetId);
                    const line = document.getElementById('line-' + targetId);
                    if (dot && line) {
                        updateLine(activeLabel, dot, line);
                    }
                });
            }, 100); // 停止縮放 100ms 後才執行
    };
    
    window.addEventListener('resize', debouncedUpdate);

    // 7. 處理側邊欄開合 (也會影響座標)
    const hamburger = document.querySelector('.hamburger-menu');
    if (hamburger) {
        // 監聽側邊欄的 transition 動畫結束事件
        sidebar.addEventListener('transitionend', debouncedUpdate);
    }
    // --- *** 在這裡插入新程式碼 *** ---
    // 8. 預設啟用 "村", "莊園", "牧場"
    labels.forEach(label => {
        const labelText = label.textContent || label.innerText;
        // 根據您 200.html 的設定，牧場也設為紅色，所以一併加入
        if (labelText.includes('村') || labelText.includes('莊園') || labelText.includes('城')) { 
            const targetId = label.dataset.targetId;
            const line = document.getElementById('line-' + targetId);
            if (line) {
                // 僅添加 active class，讓 onload 時的 debouncedUpdate 去繪製
                label.classList.add('active');
                line.classList.add('active');
            }
        }
    });
    // --- *** 新程式碼結束 *** ---
    
}
    function setActiveState(pageKey) {
        if (!pageKey) return;
        document.querySelectorAll('.sidebar li').forEach(i => i.classList.remove('active'));
        document.querySelectorAll('.sidebar a').forEach(a => a.classList.remove('active'));

        const activeLink = document.querySelector(`a[data-page="${pageKey}"]`);
        if (activeLink) {
            activeLink.classList.add('active');
            let parent = activeLink.closest('.nav-item');
            if (parent) parent.classList.add('open');

            let subParent = activeLink.closest('.has-children');
            if (subParent) {
                subParent.classList.add('open');
                const mainLink = subParent.querySelector('a');
                if(mainLink) mainLink.classList.add('active');
            }
        }
    }

    function handleHashChange() {
        const pageKey = window.location.hash.substring(1);
        const defaultPage = 'intro/about';
        const pageToLoad = pageKey || defaultPage;
        loadPage(pageToLoad);
        setActiveState(pageToLoad);
    }
    
    navItems.forEach(item => {
        const title = item.querySelector('.nav-title');
        if (title) {
            title.addEventListener('click', function() {
                const wasOpen = item.classList.contains('open');
                navItems.forEach(i => i.classList.remove('open'));
                if (!wasOpen) { item.classList.add('open'); }
            });
        }
    });

    subMenuParents.forEach(item => {
        const toggle = item.querySelector('.submenu-title-toggle');
        
        // 讓我們也讓標題可以被點擊 (針對您新的地圖分類)
        const title = item.querySelector('.submenu-category-title'); 

        const clickLogic = function(e) {
            e.stopPropagation(); // 防止點擊穿透
            
            const wasOpen = item.classList.contains('open');
            
            // 關鍵：找到 *同層級* 的所有 .has-children 項目並關閉它們
            const parentSubmenu = item.closest('.submenu');
            if (parentSubmenu) {
                const allSiblings = parentSubmenu.querySelectorAll('.has-children');
                allSiblings.forEach(i => i.classList.remove('open'));
            }
            
            // 如果點擊的不是一個已經打開的，就打開它
            if (!wasOpen) {
                item.classList.add('open');
            }
        };

        if(toggle) {
            toggle.addEventListener('click', clickLogic);
        }
        if(title) {
            title.addEventListener('click', clickLogic);
        }
    });

    if (hamburger && sidebar) {
        hamburger.addEventListener('click', function() {
            sidebar.classList.toggle('open');
        });
    }

    if (sidebar) {
        sidebar.addEventListener('click', function(e) {
            if (e.target.tagName === 'A') {
                if (sidebar.classList.contains('open')) {
                    sidebar.classList.remove('open');
                }
            }
        });
    }

    window.addEventListener('hashchange', handleHashChange);
    handleHashChange();
});