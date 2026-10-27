import {initComments} from './comments.js';
import {initLikes} from './likes.js';

initLikes(document.querySelector('article.post'));
initComments();
