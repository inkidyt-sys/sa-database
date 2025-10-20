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
                if (pagePath === 'monsters/mondex') {
                    initializeMondexLogic();
                }
            } else {
                mainContent.innerHTML = `<h1>錯誤 404</h1><p>找不到頁面: <code>${filePath}</code></p>`;
            }
        } catch (error) {
            console.error('載入頁面時發生錯誤:', error);
            mainContent.innerHTML = `<h1>載入錯誤</h1><p>無法載入頁面內容。</p>`;
        }
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
        if(toggle){
            toggle.addEventListener('click', function(e){
                e.stopPropagation();
                item.classList.toggle('open');
            });
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