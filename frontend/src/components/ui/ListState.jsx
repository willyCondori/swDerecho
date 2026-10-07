import shared from '../../styles/shared.module.css'

export default function ListState({ icon = 'ti-inbox', title, text, action, classes = shared }) {
  return <div className={classes.emptyState}>
    <i className={`ti ${icon} ${classes.emptyIcon}`} aria-hidden="true" />
    {title && <p className={classes.emptyTitle}>{title}</p>}
    <p className={classes.emptyText}>{text}</p>
    {action}
  </div>
}
