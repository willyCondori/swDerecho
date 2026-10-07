import shared from '../../styles/shared.module.css'

export default function PageHeader({ title, subtitle, children, classes = shared }) {
  return <header className={classes.header}>
    <div>
      <h1 className={classes.title}>{title}</h1>
      {subtitle && <p className={classes.subtitle}>{subtitle}</p>}
    </div>
    {children && <div className={classes.headerActions}>{children}</div>}
  </header>
}
