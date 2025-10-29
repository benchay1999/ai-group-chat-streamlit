/**
 * Translation dictionaries for English and Korean
 */

const translations = {
  english: {
    // Lobby Page
    'lobby.title': 'Group Chat',
    'lobby.subtitle': 'Find a room or create your own',
    'lobby.serverOnline': 'Server Online',
    'lobby.serverOffline': 'Server Offline',
    'lobby.createRoom': 'Create Room',
    'lobby.availableRooms': 'Available Rooms',
    'lobby.refresh': 'Refresh',
    'lobby.refreshing': 'Refreshing...',
    'lobby.loading': 'Loading rooms...',
    'lobby.noRooms': 'No rooms available',
    'lobby.noRoomsSubtitle': 'Be the first to create one!',
    'lobby.previous': 'Previous',
    'lobby.next': 'Next',
    'lobby.page': 'Page',
    'lobby.of': 'of',
    
    // Game Description
    'game.banner.title': 'Can You Find the AI?',
    'game.banner.description': 'Join a group chat with AI bots and other humans. Chat, analyze behavior, and vote for who you think is the most human-like player. Humans win if they successfully identify a human. AIs win if they trick you into voting for an AI!',
    'game.banner.challenge': 'The Challenge:',
    'game.banner.chat': 'Chat & Discuss',
    'game.banner.analyze': 'Analyze Behavior',
    'game.banner.vote': 'Vote to Eliminate',
    
    // Room Card
    'room.waiting': 'Waiting',
    'room.players': 'Players',
    'room.totalPlayers': 'Total Players',
    'room.aiPlayers': 'AI Players',
    'room.code': 'Code',
    'room.joinRoom': 'Join Room',
    'room.language': 'Language',
    'room.english': 'English',
    'room.korean': 'Korean',
    
    // Create Room Modal
    'modal.title': 'Create New Room',
    'modal.maxHumans': 'Maximum Human Players',
    'modal.totalPlayers': 'Total Players',
    'modal.language': 'Chat Language',
    'modal.preview': 'Room Preview',
    'modal.humanPlayers': 'Human Players',
    'modal.aiPlayers': 'AI Players',
    'modal.total': 'Total',
    'modal.cancel': 'Cancel',
    'modal.create': 'Create Room',
    'modal.creating': 'Creating...',
    
    // Player List
    'player.players': 'Players',
    'player.active': 'active',
    'player.you': 'You',
    'player.voted': 'Voted',
    'player.eliminated': 'Eliminated',
    'player.voteButton': 'Vote as Most Human',
    'player.leaveRoom': 'Leave Room',
    
    // Game Phases
    'phase.discussion': 'Discussion',
    'phase.voting': 'Voting',
    'phase.elimination': 'Elimination',
    'phase.gameOver': 'Game Over',
    
    // Messages
    'message.roomCreated': 'Room created',
    'message.joinedAs': 'Joined as',
    'message.failedToLoadRooms': 'Failed to load rooms',
    'message.failedToCreateRoom': 'Failed to create room',
    'message.failedToJoin': 'Failed to join created room',
  },
  
  korean: {
    // Lobby Page
    'lobby.title': '그룹 채팅',
    'lobby.subtitle': '방을 찾거나 직접 만드세요',
    'lobby.serverOnline': '서버 온라인',
    'lobby.serverOffline': '서버 오프라인',
    'lobby.createRoom': '방 만들기',
    'lobby.availableRooms': '사용 가능한 방',
    'lobby.refresh': '새로고침',
    'lobby.refreshing': '새로고침 중...',
    'lobby.loading': '방 로딩 중...',
    'lobby.noRooms': '사용 가능한 방이 없습니다',
    'lobby.noRoomsSubtitle': '첫 번째로 방을 만들어보세요!',
    'lobby.previous': '이전',
    'lobby.next': '다음',
    'lobby.page': '페이지',
    'lobby.of': '/',
    
    // Game Description
    'game.banner.title': 'AI를 찾을 수 있나요?',
    'game.banner.description': 'AI 봇과 다른 인간들과 함께 그룹 채팅에 참여하세요. 채팅하고, 행동을 분석하고, 가장 인간다운 플레이어에게 투표하세요. 인간이 인간을 성공적으로 식별하면 인간이 승리합니다. AI가 당신을 속여 AI에게 투표하게 만들면 AI가 승리합니다!',
    'game.banner.challenge': '도전 과제:',
    'game.banner.chat': '채팅 & 토론',
    'game.banner.analyze': '행동 분석',
    'game.banner.vote': '투표하여 제거',
    
    // Room Card
    'room.waiting': '대기 중',
    'room.players': '플레이어',
    'room.totalPlayers': '전체 플레이어',
    'room.aiPlayers': 'AI 플레이어',
    'room.code': '코드',
    'room.joinRoom': '방 참가',
    'room.language': '언어',
    'room.english': '영어',
    'room.korean': '한국어',
    
    // Create Room Modal
    'modal.title': '새 방 만들기',
    'modal.maxHumans': '최대 인간 플레이어 수',
    'modal.totalPlayers': '전체 플레이어 수',
    'modal.language': '채팅 언어',
    'modal.preview': '방 미리보기',
    'modal.humanPlayers': '인간 플레이어',
    'modal.aiPlayers': 'AI 플레이어',
    'modal.total': '전체',
    'modal.cancel': '취소',
    'modal.create': '방 만들기',
    'modal.creating': '생성 중...',
    
    // Player List
    'player.players': '플레이어',
    'player.active': '활성',
    'player.you': '나',
    'player.voted': '투표함',
    'player.eliminated': '제거됨',
    'player.voteButton': '가장 인간답다고 투표',
    'player.leaveRoom': '방 나가기',
    
    // Game Phases
    'phase.discussion': '토론',
    'phase.voting': '투표',
    'phase.elimination': '제거',
    'phase.gameOver': '게임 종료',
    
    // Messages
    'message.roomCreated': '방이 생성되었습니다',
    'message.joinedAs': '참가했습니다:',
    'message.failedToLoadRooms': '방 로딩에 실패했습니다',
    'message.failedToCreateRoom': '방 생성에 실패했습니다',
    'message.failedToJoin': '방 참가에 실패했습니다',
  }
};

/**
 * Get translation for a key
 * @param {string} language - 'english' or 'korean'
 * @param {string} key - Translation key (e.g., 'lobby.title')
 * @returns {string} Translated string
 */
export function getTranslation(language, key) {
  const lang = language === 'korean' ? 'korean' : 'english';
  return translations[lang][key] || key;
}

/**
 * Get all translations for a language
 * @param {string} language - 'english' or 'korean'
 * @returns {object} Translation dictionary
 */
export function getAllTranslations(language) {
  const lang = language === 'korean' ? 'korean' : 'english';
  return translations[lang];
}

export default translations;

